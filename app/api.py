from typing import Annotated
import networkx as nx
from fastapi import FastAPI, Body, HTTPException, Query, Response, status
from pydantic import BaseModel
from plot import PlotterType, get_plotter
from model import Track
from solver import SingleTrackOptimizerType, SingleTrackSolution, get_single_track_optimizer

from sample import load_network
from fastapi import Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os


# This will be our in-memory database. TODO: Use a real database
tracks: dict[str, Track] = {}
# This will be our in-memory cache. TODO: Use a real database
topologies: dict[str, SingleTrackSolution] = {}

topo = os.path.join("datasource", os.getenv("TOPOFILE", "azure_geant_topo.yaml"))
network = load_network(topo)

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

class SingleTrackSolutionDTO(BaseModel):
    cost: float
    max_delay: float
    used_links: list[tuple[str, str]]
    
class Origin(BaseModel):
    url: str


def get_track_namespace(track_namespace: str) -> str:
    return f"{track_namespace}"


@app.get("/network", status_code=status.HTTP_200_OK)
async def get_network() -> NetworkDTO:
    nodes = list(map(lambda node_attr: NodeDTO(name=node_attr[0], attributes=node_attr[1]), network.nodes(data=True)))
    edges = list(map(lambda edge_attr: EdgeDTO(src=edge_attr[0], dst=edge_attr[1], attributes=edge_attr[2]), network.edges(data=True)))
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
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    return TrackDTO(publisher=track.publisher, delay_budget=track.delay_budget)


@app.get("/tracks/{track_namespace}/topology", status_code=status.HTTP_200_OK)
async def get_topology_for_track(track_namespace: str) -> SingleTrackSolutionDTO:
    solution = topologies.get(track_namespace, None)
    if solution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")
    return SingleTrackSolutionDTO(cost=solution.cost, max_delay=solution.max_delay, used_links=solution.used_links)


@app.get("/tracks/{track_namespace}/topology/plot", status_code=status.HTTP_200_OK)
async def get_topology_plot(track_namespace: str, plotter_type: Annotated[PlotterType | None, Query()] = PlotterType.BASEMAP) -> bytes:
    track = tracks.get(track_namespace, None)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Track namespace not found")

    used_links = (await get_topology_for_track(track_namespace)).used_links
    plotter = get_plotter(plotter_type)
    image_bytes = plotter(network, {track.publisher, *track.subscribers}, set(network.edges), set(used_links), "red")
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

    # Memoization of used links per track
    if subscriber not in track.subscribers:
        track.add_subscriber(subscriber)

        solution = optimize(network, track, optimizer_type, reduce_network)
        if not solution.success:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Optimization failed")

        topologies[track_namespace] = solution

    next_hop = next(map(lambda edge: edge[0], filter(
        lambda edge, subscriber=subscriber: edge[1] == subscriber, topologies[track_namespace].used_links)), None)
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


@app.get("/origin/{relay_id}/{namespace}")
async def get_origin(relay_id: int, namespace: str):
    nodes = network.nodes

    if relay_id > len(nodes):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such relay")
    relay_in = list(nodes)[relay_id - 1]
    
    response = await subscribe_to_track(track_namespace=namespace, subscriber=relay_in)

    try:
        relay_out_id = list(nodes).index(response) + 1
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such relay")
    
    if response is not None:
        response_json = {"url": f"https://10.3.0.{relay_out_id}:4443/"}
        return JSONResponse(content=response_json, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


@app.post("/origin/{relay_id}/{namespace}", status_code=status.HTTP_200_OK)
async def set_origin(relay_id: int, namespace: str, origin: Annotated[Origin, Body()]):
    nodes = network.nodes

    if relay_id > len(nodes):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such relay")
    relay = list(nodes)[relay_id - 1]
    
    delay_budget = float(namespace.split("_")[2]) if "_" in namespace else 0.0

    response = await create_track(
        track_namespace=namespace,
        track_dto=TrackDTO(
            publisher=relay,
            delay_budget=delay_budget
        ))
    if response is not None:
        response_json = {"url": f"https://10.3.0.{relay_id}/"}
        return JSONResponse(content=response_json)
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    

@app.delete("/origin/{relayid}/{namespace}", status_code=status.HTTP_204_NO_CONTENT)
async def del_origin(relayid: int, namespace: str, origin: Annotated[Origin, Body()]):
    await unsubscribe_to_track(track_namespace=namespace, subscriber=relayid)
