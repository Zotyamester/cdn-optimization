import math
import networkx as nx
import random
from model import Track


def generate_full_mesh_traffic(peers: list[str], delay_budget: float):
    tracks = {}
    for i, peer in enumerate(peers, start=1):
        other_peers = list(filter(lambda x, peer=peer: x != peer, peers))
        tracks[f"t{i}"] = Track(
            publisher=peer,
            initial_subscribers=other_peers,
            delay_budget=delay_budget
        )
    return tracks


def generate_broadcast_traffic(track_id: str, publisher: str, subscribers: list[str], delay_budget: float = 2000.0) -> dict[str, Track]:
    tracks = {
        track_id: Track(
            publisher=publisher,
            initial_subscribers=subscribers,
            delay_budget=delay_budget
        )
    }
    return tracks


def generate_circle_edge_relays(network: nx.DiGraph, count: int) -> list[tuple[str, dict[str, tuple[float, float]]]]:
    latitudes = [lat for lat, _ in nx.get_node_attributes(network, "location").values()]
    longitudes = [lon for _, lon in nx.get_node_attributes(network, "location").values()]
    bounding_box = (min(latitudes), max(latitudes), min(longitudes), max(longitudes))

    inscribed_circle_radius = min(
        (bounding_box[1] - bounding_box[0]) / 2,
        (bounding_box[3] - bounding_box[2]) / 2
    )
    inscribed_circle_center = (
        (bounding_box[0] + bounding_box[1]) / 2,
        (bounding_box[2] + bounding_box[3]) / 2
    )

    relays = []
    
    for i in range(0, count):
        angle = 2 * 3.14159 * i / count
        lat = inscribed_circle_center[0] + inscribed_circle_radius * math.cos(angle)
        lon = inscribed_circle_center[1] + inscribed_circle_radius * math.sin(angle)
        relays.append((f"relay{i}", {"location": (lat, lon)}))

    return relays


def generate_point_of_presence_relays(network: nx.DiGraph) -> list[tuple[str, dict[str, tuple[float, float]]]]:
    relays = []

    for i, (node, attrs) in enumerate(network.nodes(data=True)):
        relays.append((f"relay{i}", {"location": attrs["location"]}))

    return relays


def choose_peers(network: nx.DiGraph, count: int, seed: int | None = None) -> list[str]:
    if seed is not None:
        random.seed(seed)
    return random.sample(list(network.nodes), k=count)
