import itertools
from collections import defaultdict
import json
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
                 calculate_latency: Callable[[
                     nx.DiGraph, str, str], float] = default_calculate_latency,
                 calculate_cost: Callable[[nx.DiGraph, str, str], float] = default_calculate_cost) -> nx.DiGraph:
    mapped_graph = nx.DiGraph()

    graph: nx.DiGraph = nx.read_graphml(graph_path)

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

def load_geant_json(graph_path: str,
                    calculate_latency: Callable[[nx.DiGraph, str, str], float] = default_calculate_latency) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()

    with open(graph_path, "r") as json_file:
        model = json.load(json_file)

    for node in model["cities"]:
        graph.add_node(node["id"], location=(float(node["lat"]), float(node["long"])))
    
    for links in model["links"].values():
        for link in links:
            node1 = link["endpoint1_id"]
            node2 = link["endpoint2_id"]

            local_link_cost, global_link_cost = 1, graph.number_of_nodes()
            cost = global_link_cost if link["region"] == "global" else local_link_cost

            forward_edge = (node1, node2)
            graph.add_edge(
                *forward_edge,
                latency=calculate_latency(graph, *forward_edge),
                cost=cost
            )

            reverse_edge = (node2, node1)
            graph.add_edge(
                *reverse_edge,
                latency=calculate_latency(graph, *reverse_edge),
                cost=cost
            )
    
    return graph

def create_graph(nodes: list[tuple[str, dict]],
                 calculate_latency: Callable[[
                     nx.DiGraph, str, str], float] = default_calculate_latency,
                 calculate_cost: Callable[[nx.DiGraph, str, str], float] = default_calculate_cost) -> nx.DiGraph:
    g = nx.DiGraph()

    g.add_nodes_from(nodes)

    # Calculate cost and latency between every pair of cities and add a edge in both directions
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


def display_network_links(network: nx.DiGraph):
    print("Links:")
    for node1, node2, data in sorted(network.edges(data=True), key=lambda kv: kv[2]["latency"]):
        print(f" * {node1} <-> {node2}:\t\t{data['latency']:.2f} ms\t\t{data['cost']:.2f}")
    print()


def display_triangle_inequality_satisfaction(network: nx.DiGraph):
    cost_triangle_inequality_satisfied = 0
    latency_triangle_inequality_satisfied = 0

    for start_node in network.nodes:
        for end_node in network.nodes:
            if end_node == start_node:
                continue

            for intermediate_node in network.nodes:
                if intermediate_node == start_node or intermediate_node == end_node:
                    continue

                cost1 = network.get_edge_data(start_node, intermediate_node)["cost"]
                cost2 = network.get_edge_data(intermediate_node, end_node)["cost"]
                cost_direct = network.get_edge_data(start_node, end_node)["cost"]

                if cost1 + cost2 >= cost_direct:
                    cost_triangle_inequality_satisfied += 1
                else:
                    print(f"{start_node} -> {intermediate_node} -> {end_node}")
                    print(f"\t[C]: FAIL {cost1} + {cost2} < {cost_direct}")

                latency1 = network.get_edge_data(start_node, intermediate_node)["latency"]
                latency2 = network.get_edge_data(intermediate_node, end_node)["latency"]
                latency_direct = network.get_edge_data(start_node, end_node)["latency"]

                if latency1 + latency2 >= latency_direct:
                    latency_triangle_inequality_satisfied += 1
                else:
                    print(f"{start_node} -> {intermediate_node} -> {end_node}")
                    print(f"\t[L]: FAIL {latency1} + {latency2} < {latency_direct}")

    n = len(network.nodes)
    total = n * (n - 1) * (n - 2)  # n choose 3 * 3! => variation
    print(f"[C]: {cost_triangle_inequality_satisfied} / {total} satisfied.")
    print(f"[L]: {latency_triangle_inequality_satisfied} / {total} satisfied.")


class Track:
    def __init__(self, publisher: str, initial_subscribers: list[str], delay_budget: float):
        self.delay_budget = delay_budget
        self.publisher = publisher

        self.subscribers = set()
        self.streams = dict()
        for i, subscriber in enumerate(initial_subscribers, start=1):
            stream_id = f"f{i}"
            self.add_subscriber(subscriber, stream_id)

    def add_subscriber(self, subscriber: str, stream_id: str | None = None):
        self.subscribers.add(subscriber)

        if stream_id is None:
            stream_id = f"f{max(map(lambda sid: int(sid[1:]), self.streams.keys()), default=0) + 1}"
        self.streams[stream_id] = defaultdict(
            lambda: 0,
            {
                self.publisher: -1,
                subscriber: 1
            }
        )

    def remove_subscriber(self, subscriber: str):
        self.subscribers.remove(subscriber)
        self.streams = {
            stream_id: stream
            for stream_id, stream in self.streams.items()
            if subscriber not in stream
        }

    def __iter__(self):
        yield from (self.publisher, self.subscribers)

    def __str__(self) -> str:
        return f"Track with delay_budget of {self.delay_budget}: " \
            f"{self.publisher} -> [{', '.join(self.subscribers)}]"

    def __repr__(self) -> str:
        return str(self)


def display_tracks_stats(tracks: dict[str, Track]):
    print("Track:")
    for track_id, (publisher, subscribers) in tracks.items():
        print(f"\t{track_id}: {publisher} -> [{', '.join(subscribers)}]")
