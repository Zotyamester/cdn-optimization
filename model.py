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
    return 1.0


def load_graphml(graph_path: str,
                 calculate_latency: Callable[[nx.DiGraph, str, str], float] = default_calculate_latency,
                 calculate_cost: Callable[[nx.DiGraph, str, str], float] = default_calculate_cost) -> nx.DiGraph:
    mapped_graph = nx.DiGraph()

    graph: nx.Graph = nx.read_graphml(graph_path)

    # Add the nodes from the base graph.
    for node, data in graph.nodes(data=True):
        if "Longitude" in data and "Latitude" in data:
            location = (data["Latitude"], data["Longitude"])
            mapped_graph.add_node(node, location=location)

    # Add the edges from the base graph.
    for node1, node2 in graph.edges(data=False):
        if node1 in mapped_graph.nodes and node2 in mapped_graph.nodes:
            forward_edge = (node1, node2)
            mapped_graph.add_edge(
                *forward_edge,
                latency=calculate_latency(mapped_graph, *forward_edge),
                cost=calculate_cost(mapped_graph, *forward_edge)
            )

            reverse_edge = (node2, node1)
            mapped_graph.add_edge(
                *reverse_edge,
                latency=calculate_latency(mapped_graph, *reverse_edge),
                cost=calculate_cost(mapped_graph, *reverse_edge)
            )
    
    return mapped_graph


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


def display_triangle_inequality_satisfaction(network: nx.DiGraph):
    triangle_inequality_satisfied = 0

    for start_node in network.nodes:
        for end_node in network.nodes:
            if end_node == start_node:
                continue

            for intermediate_node in network.nodes:
                if intermediate_node == start_node or intermediate_node == end_node:
                    continue

                cost1 = default_calculate_cost(
                    network, start_node, intermediate_node)
                cost2 = default_calculate_cost(
                    network, intermediate_node, end_node)
                cost_direct = default_calculate_cost(
                    network, start_node, end_node)

                print(f"{start_node} -> {intermediate_node} -> {end_node}")
                if cost1 + cost2 >= cost_direct:
                    print("\tOK")
                    triangle_inequality_satisfied += 1
                else:
                    print("\nFAIL")

    n = len(network.nodes)
    total = n * (n - 1) * (n - 2)  # n choose 3 * 3! => variation
    print(f"{triangle_inequality_satisfied} / {total} satisfied.")
