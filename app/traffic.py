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


def generate_continental_relays(number_of_continents: int, relay_per_continent: int, seed: int | None = None) -> list[tuple[str, dict[str, tuple[float, float]]]]:
    if seed is not None:
        random.seed(seed)
    
    CONTINENTS = {
        "North_Europe": {"lat_range": (50, 70), "lon_range": (-10, 30)},
        "South_Europe": {"lat_range": (35, 50), "lon_range": (-10, 40)},
        "North_America": {"lat_range": (25, 50), "lon_range": (-130, -60)},
        "South_America": {"lat_range": (-55, 10), "lon_range": (-80, -35)},
        "Asia": {"lat_range": (10, 60), "lon_range": (60, 150)},
        "Africa": {"lat_range": (-35, 35), "lon_range": (-20, 55)},
        "Australia": {"lat_range": (-50, -10), "lon_range": (110, 160)},
    }

    def generate_location(continent, ranges):
        lat = random.uniform(*ranges["lat_range"])
        lon = random.uniform(*ranges["lon_range"])
        return (continent, {"location": (round(lat, 4), round(lon, 4))})

    relays = []
    for continent, ranges in random.sample(list(CONTINENTS.items()), k=number_of_continents):
        for i in range(relay_per_continent):
            relays.append(generate_location(f"{continent}-{i}", ranges))
    return relays


def generate_point_of_presence_relays(network: nx.DiGraph) -> list[tuple[str, dict[str, tuple[float, float]]]]:
    relays = []

    for i, (_, attrs) in enumerate(network.nodes(data=True)):
        relays.append((f"relay{i}", {"location": attrs["location"]}))

    return relays


def choose_peers(network: nx.DiGraph, count: int, seed: int | None = None) -> list[str]:
    if seed is not None:
        random.seed(seed)
    return random.sample(list(network.nodes), k=count)
