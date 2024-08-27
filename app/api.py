from typing import Annotated
import networkx as nx
from fastapi import FastAPI, Body, HTTPException, Query, status
from pydantic import BaseModel
from gcp_sample import network
from model import Track
# This is a static network. TODO: Make it dynamic, use a database.
from solver import SingleTrackOptimizer, SingleTrackSolution, get_single_track_optimizer
tracks = {}  # This will be our in-memory database. TODO: Use a real database
used_links_per_track = {}  # This will be our in-memory cache. TODO: Use a real database

app = FastAPI()


class NodeDTO(BaseModel):
    name: str
    attributes: dict


class EdgeDTO(BaseModel):
    src: str
    dst: str
    attributes: dict


class NetworkDTO(BaseModel):
    nodes: list[NodeDTO]
    edges: list[EdgeDTO]


class TrackDTO(BaseModel):
    name: str
    publisher: str
    delay_budget: float


def get_track_id(track_namespace: str, track_name: str) -> str:
    return f"{track_namespace}:{track_name}"


@app.get("/network", status_code=status.HTTP_200_OK)
async def get_network() -> NetworkDTO:
    nodes = list(map(lambda node_attr: NodeDTO(
        name=node_attr[0], attributes=node_attr[1]), network.nodes(data=True)))
    edges = list(map(lambda edge_attr: EdgeDTO(
        src=edge_attr[0], dst=edge_attr[1], attributes=edge_attr[2]), network.edges(data=True)))
    return NetworkDTO(nodes=nodes, edges=edges)


@app.get("/tracks", status_code=status.HTTP_200_OK)
async def get_tracks() -> list[TrackDTO]:
    return list(map(lambda track: TrackDTO(name=track.name, publisher=track.publisher, delay_budget=track.delay_budget), tracks.values()))


@app.post("/tracks/{track_namespace}/{track_name}", status_code=status.HTTP_201_CREATED)
async def create_track(track_namespace: str, track_name: str, track_dto: Annotated[TrackDTO, Body()]) -> TrackDTO | None:
    track_id = get_track_id(track_namespace, track_name)
    track = Track(track_dto.name, track_dto.publisher,
                  [], track_dto.delay_budget)
    tracks[track_id] = track
    return track_dto


@app.get("/tracks/{track_namespace}/{track_name}", status_code=status.HTTP_200_OK)
async def get_track(track_namespace: str, track_name: str) -> TrackDTO:
    track_id = get_track_id(track_namespace, track_name)
    track = tracks.get(track_id, None)
    if track == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return TrackDTO(name=track.name, publisher=track.publisher, delay_budget=track.delay_budget)


@app.get("/tracks/{track_namespace}/{track_name}/topology", status_code=status.HTTP_200_OK)
async def get_topology_for_track(track_namespace: str, track_name: str) -> list:
    track_id = get_track_id(track_namespace, track_name)
    used_links = used_links_per_track.get(track_id, None)
    if used_links is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return used_links


def optimize(network: nx.DiGraph, track: Track, optimizer_type: SingleTrackOptimizer = SingleTrackOptimizer.INTEGER_LINEAR_PROGRAMMING, reduce_network: bool = False) -> SingleTrackSolution:
    if reduce_network:
        network = network.copy()
        network.remove_nodes_from({track.publisher, *track.subscribers} - {*network.nodes})
    optimizer = get_single_track_optimizer(optimizer_type)
    return optimizer(network, track)


@app.post("/tracks/{track_namespace}/{track_name}/subscribe", status_code=status.HTTP_200_OK)
async def subscribe_to_track(track_namespace: str, track_name: str, subscriber: Annotated[str, Body()],
                             optimizer_type: Annotated[SingleTrackOptimizer | None, Query()] = SingleTrackOptimizer.INTEGER_LINEAR_PROGRAMMING,
                             reduce_network: Annotated[bool | None, Query()] = False) -> str:
    track_id = get_track_id(track_namespace, track_name)
    track = tracks.get(track_id, None)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

    track.add_subscriber(subscriber)

    solution = optimize(network, track, optimizer_type, reduce_network)
    if not solution.success:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT, detail="Optimization failed")

    used_links_per_track[track_id] = solution.used_links
    next_hop = next(map(lambda edge: edge[0], filter(
        lambda edge, subscriber=subscriber: edge[1] == subscriber, solution.used_links)), None)
    if next_hop == None:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT,
                            detail="Next hop cannot be determined")

    return next_hop


@app.post("/tracks/{track_namespace}/{track_name}/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_to_track(track_namespace: str, track_name: str, subscriber: Annotated[str, Body()]):
    track_id = get_track_id(track_namespace, track_name)
    tracks[track_id].remove_subscriber(subscriber)
