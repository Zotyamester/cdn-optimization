import itertools
from collections import defaultdict
from typing import Callable

import geopy.distance
import networkx as nx


def default_calculate_latency(g: nx.DiGraph, node1: str, node2: str) -> float:
    LINK_PROPAGATION_SPEED = 200_000  # in km/s
    coords1 = g.nodes[node1]["location"]
    coords2 = g.nodes[node2]["location"]

    distance = geopy.distance.geodesic(coords1, coords2).km
    latency_in_s = distance / LINK_PROPAGATION_SPEED
    latency_in_ms = latency_in_s * 1000

    return latency_in_ms


def default_calculate_cost(g: nx.DiGraph, node1: str, node2: str) -> float:
    egress_cost_of_sender = g.nodes[node1]["egress_cost"]
    ingress_cost_of_receiver = g.nodes[node2]["ingress_cost"]

    return egress_cost_of_sender + ingress_cost_of_receiver


def create_graph(nodes: list[tuple[str, dict]],
                 calculate_latency: Callable[[
                     nx.DiGraph, str, str], float] = default_calculate_latency,
                 calculate_cost: Callable[[nx.DiGraph, str, str], float] = default_calculate_cost) -> nx.DiGraph:
    g = nx.DiGraph()

    g.add_nodes_from(nodes)

    # Calculate distance between every pair of cities and add a edge in both directions
    for node1, node2 in itertools.combinations(g.nodes, 2):
        forward_edge = (node1, node2)
        g.add_edge(
            *forward_edge,
            latency=calculate_latency(g, *forward_edge),
            cost=calculate_cost(g, *forward_edge)
        )

        reverse_edge = (node2, node1)
        g.add_edge(
            *reverse_edge,
            latency=calculate_latency(g, *reverse_edge),
            cost=calculate_cost(g, *reverse_edge)
        )

    return g


class Track:
    def __init__(self, name: str, publisher: str, subscribers: list[str], delay_budget: float):
        self.name = name
        self.publisher = publisher
        self.subscribers = subscribers
        self.delay_budget = delay_budget
        self.recreate_streams()

    def recreate_streams(self):
        self.streams = {}
        for i, subscriber in enumerate(self.subscribers, start=1):
            stream_id = f"f{i}"
            self.streams[stream_id] = defaultdict(
                lambda: 0,
                {
                    self.publisher: -1,
                    subscriber: 1
                }
            )

    def __iter__(self):
        yield from (self.name, self.publisher, self.subscribers)

    def __str__(self) -> str:
        return f"Track {self.name} with delay_budget of {self.delay_budget}: " \
            f"{self.publisher} -> [{', '.join(self.subscribers)}]"

    def __repr__(self) -> str:
        return str(self)


def display_network_links(network: nx.DiGraph):
    print("Links:")
    for node1, node2, data in sorted(network.edges(data=True), key=lambda kv: kv[2]["latency"]):
        print(f" * {node1} <-> {node2}:\t\t{data["latency"]:.2f} ms\t\t{data["cost"]:.2f}")
    print()


def display_tracks_stats(tracks: dict[str, Track]):
    print("Track:")
    for track_id, (name, publisher, subscribers) in tracks.items():
        print(f"\t{track_id} ({name}): {
              publisher} -> [{', '.join(subscribers)}]")
