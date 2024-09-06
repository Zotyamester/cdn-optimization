from typing import Annotated
import networkx as nx
from fastapi import FastAPI, Body, HTTPException, Query, Response, status
from pydantic import BaseModel
from app.plot import PlotterType, get_plotter
from model import Track
from solver import SingleTrackOptimizerType, SingleTrackSolution, get_single_track_optimizer

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
    publisher: str
    delay_budget: float


def get_track_namespace(track_namespace: str) -> str:
    return f"{track_namespace}"


@app.get("/network", status_code=status.HTTP_200_OK)
async def get_network() -> NetworkDTO:
    nodes = list(map(lambda node_attr: NodeDTO(attributes=node_attr[1]), network.nodes(data=True)))
    edges = list(map(lambda edge_attr: EdgeDTO(
        src=edge_attr[0], dst=edge_attr[1], attributes=edge_attr[2]), network.edges(data=True)))
    return NetworkDTO(nodes=nodes, edges=edges)


@app.get("/tracks", status_code=status.HTTP_200_OK)
async def get_tracks() -> list[TrackDTO]:
    return list(map(lambda track: TrackDTO(publisher=track.publisher, delay_budget=track.delay_budget), tracks.values()))


@app.post("/tracks/{track_namespace}", status_code=status.HTTP_201_CREATED)
async def create_track(track_namespace: str, track_dto: Annotated[TrackDTO, Body()]) -> TrackDTO | None:
    track = Track(track_dto.publisher, [], track_dto.delay_budget)
    tracks[track_namespace] = track
    return track_dto


@app.get("/tracks/{track_namespace}", status_code=status.HTTP_200_OK)
async def get_track(track_namespace: str) -> TrackDTO:
    track = tracks.get(track_namespace, None)
    if track == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    return TrackDTO(publisher=track.publisher, delay_budget=track.delay_budget)


@app.get("/tracks/{track_namespace}/topology", status_code=status.HTTP_200_OK)
async def get_topology_for_track(track_namespace: str) -> list:
    used_links = used_links_per_track.get(track_namespace, None)
    if used_links is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    return used_links


@app.get("/tracks/{track_namespace}/topology/plot", status_code=status.HTTP_200_OK)
async def get_topology_plot(track_namespace: str, plotter_type: Annotated[PlotterType | None, Query()] = PlotterType.BASEMAP) -> bytes:
    used_links = await get_topology_for_track(track_namespace)
    plotter = get_plotter(plotter_type)
    image_bytes = plotter(network, set(network.nodes), set(network.edges), set(used_links), "red")
    return Response(content=image_bytes, media_type="image/png")


def optimize(network: nx.DiGraph, track: Track,
             optimizer_type: SingleTrackOptimizerType = SingleTrackOptimizerType.INTEGER_LINEAR_PROGRAMMING,
             reduce_network: bool = False) -> SingleTrackSolution:
    if reduce_network:
        network = network.copy()
        network.remove_nodes_from(
            {track.publisher, *track.subscribers} - {*network.nodes})
    optimizer = get_single_track_optimizer(optimizer_type)
    return optimizer(network, track)


@app.post("/tracks/{track_namespace}/subscription/{subscriber}", status_code=status.HTTP_200_OK)
async def subscribe_to_track(track_namespace: str, subscriber: str,
                             optimizer_type: Annotated[SingleTrackOptimizerType | None, Query(
                             )] = SingleTrackOptimizerType.INTEGER_LINEAR_PROGRAMMING,
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


@app.delete("/tracks/{track_namespace}/subscription/{subscriber}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_to_track(track_namespace: str, subscriber: str):
    track = tracks.get(track_namespace, None)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    if subscriber not in track.subscribers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Relay is not in track namespace")

    track.remove_subscriber(subscriber)
