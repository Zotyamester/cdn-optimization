from typing import Annotated
import networkx as nx
from fastapi import FastAPI, Body, HTTPException, Query, status
from pydantic import BaseModel
from model import Track
from solver import SingleTrackOptimizer, SingleTrackSolution, get_single_track_optimizer

# This is a static network. TODO: Make it dynamic, use a database.
from gcp_sample import network

# This will be our in-memory database. TODO: Use a real database
tracks: dict[str, Track] = {}
# This will be our in-memory cache. TODO: Use a real database
used_links_per_track: dict[str, list[tuple[str, str]]] = {}


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


def get_track_namespace(track_namespace: str) -> str:
    return f"{track_namespace}"


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


@app.post("/tracks/{track_namespace}", status_code=status.HTTP_201_CREATED)
async def create_track(track_namespace: str, track_dto: Annotated[TrackDTO, Body()]) -> TrackDTO | None:
    track = Track(track_dto.name, track_dto.publisher,
                  [], track_dto.delay_budget)
    tracks[track_namespace] = track
    return track_dto


@app.get("/tracks/{track_namespace}", status_code=status.HTTP_200_OK)
async def get_track(track_namespace: str) -> TrackDTO:
    track = tracks.get(track_namespace, None)
    if track == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    return TrackDTO(name=track.name, publisher=track.publisher, delay_budget=track.delay_budget)


@app.get("/tracks/{track_namespace}/topology", status_code=status.HTTP_200_OK)
async def get_topology_for_track(track_namespace: str) -> list:
    used_links = used_links_per_track.get(track_namespace, None)
    if used_links is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    return used_links


def optimize(network: nx.DiGraph, track: Track, optimizer_type: SingleTrackOptimizer = SingleTrackOptimizer.INTEGER_LINEAR_PROGRAMMING, reduce_network: bool = False) -> SingleTrackSolution:
    if reduce_network:
        network = network.copy()
        network.remove_nodes_from(
            {track.publisher, *track.subscribers} - {*network.nodes})
    optimizer = get_single_track_optimizer(optimizer_type)
    return optimizer(network, track)


@app.post("/tracks/{track_namespace}/subscribe", status_code=status.HTTP_200_OK)
async def subscribe_to_track(track_namespace: str, subscriber: Annotated[str, Body()],
                             optimizer_type: Annotated[SingleTrackOptimizer | None, Query(
                             )] = SingleTrackOptimizer.INTEGER_LINEAR_PROGRAMMING,
                             reduce_network: Annotated[bool | None, Query()] = False) -> str:
    track = tracks.get(track_namespace, None)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    if subscriber in track.subscribers:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED,
                            detail="Relay is already in track namespace")

    track.add_subscriber(subscriber)

    solution = optimize(network, track, optimizer_type, reduce_network)
    if not solution.success:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Optimization failed")

    used_links_per_track[track_namespace] = solution.used_links
    next_hop = next(map(lambda edge: edge[0], filter(
        lambda edge, subscriber=subscriber: edge[1] == subscriber, solution.used_links)), None)
    if next_hop == None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail="Next hop cannot be determined")

    return next_hop


@app.post("/tracks/{track_namespace}/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_to_track(track_namespace: str, subscriber: Annotated[str, Body()]):
    track = tracks.get(track_namespace, None)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    if subscriber not in track.subscribers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Relay is not in track namespace")

    track.remove_subscriber(subscriber)
