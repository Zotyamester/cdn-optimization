import math
from typing import Callable
import geopy.distance
import networkx as nx
from plot import basemap_plot_network, save_plot
from model import default_calculate_latency, display_triangle_inequality_satisfaction


def find_closest_node(network: nx.DiGraph, cdn_node_data: dict) -> str:
    closest_node = None
    distance = math.inf
    for node, node_data in network.nodes(data=True):
        node_distance = geopy.distance.geodesic(
            cdn_node_data["location"], node_data["location"]).km
        if node_distance < distance:
            closest_node = node
            distance = node_distance
    return closest_node


def load_base_network(base_network: nx.DiGraph, network_name: str) -> nx.DiGraph:
    common_node_name_prefix = network_name.lower() + "_"
    nx.relabel_nodes(base_network, {node: common_node_name_prefix + str(node) for node in base_network.nodes}, False)
    return base_network


def create_underlay_network(base_network: nx.DiGraph,
                            cdn_nodes: list[tuple[str, dict]],
                            calculate_latency: Callable[[nx.DiGraph, str, str], float] = default_calculate_latency) -> nx.DiGraph:
    underlay = base_network.copy()  # Make a copy for several reasons, one of which is that the base network is used for selecting the connection point for the actual CDN

    # Connect the nodes of the CDN to the closest node of the base network with zero cost (the cost of access is neglegible for us)
    for cdn_node, cdn_node_data in cdn_nodes:
        closest_node = find_closest_node(base_network, cdn_node_data)
        if closest_node is None:
            continue

        underlay.add_node(cdn_node, location=cdn_node_data["location"])

        forward_edge = (cdn_node, closest_node)
        underlay.add_edge(
            *forward_edge,
            latency=calculate_latency(underlay, *forward_edge),
            cost=0
        )

        reverse_edge = (closest_node, cdn_node)
        underlay.add_edge(
            *reverse_edge,
            latency=calculate_latency(underlay, *reverse_edge),
            cost=0
        )

    return underlay


def create_virtual_to_physical_mapping(underlay_network: nx.DiGraph, cdn_nodes: list[tuple[str, dict]]) -> dict[tuple[str, str], list[tuple[str, str]]]:
    mapping = {}

    # O(n) * (O((n + m) * log n) + O(n)) ~ O(n^2 + n * (n + m) * log n)
    for vir_node1, _ in cdn_nodes:
        # O((n + m) * log n)
        shortest_paths = nx.shortest_path(
            underlay_network, vir_node1, weight="cost")

        # O(n) * O(n)
        for vir_node2, _ in cdn_nodes:
            if vir_node1 == vir_node2:
                continue
            edge = (vir_node1, vir_node2)
            path = shortest_paths[vir_node2]
            edge_path = [(phy_node1, phy_node2)
                         for phy_node1, phy_node2 in zip(path, path[1:])]
            mapping[edge] = edge_path

    return mapping


def create_overlay_network(underlay_network: nx.DiGraph, cdn_nodes: list[tuple[str, dict]], mapping: dict[tuple[str, str], list[tuple[str, str]]]) -> nx.DiGraph:
    overlay_network = nx.DiGraph()
    overlay_network.add_nodes_from(cdn_nodes)

    for edge, edge_path in mapping.items():
        latency, cost = 0.0, 0.0

        for (phy_node1, phy_node2) in edge_path:
            data = underlay_network.get_edge_data(phy_node1, phy_node2)
            latency += data["latency"]
            cost += data["cost"]

        overlay_network.add_edge(*edge, latency=latency, cost=cost)

    return overlay_network


if __name__ == "__main__":
    cdn_nodes = [
        ("CDN1", {"location": (52.5200, 13.4050)}),
        ("CDN2", {"location": (48.8566, 2.3522)}),
        ("CDN3", {"location": (51.5074, 0.1278)}),
        ("CDN4", {"location": (40.7128, -74.0060)}),
        ("CDN5", {"location": (34.0522, -118.243)}),
    ]
    base_network = load_base_network("./datasource/Cogentco.graphml")
    underlay_network = create_underlay_network(base_network, cdn_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, cdn_nodes)
    overlay_network = create_overlay_network(underlay_network, cdn_nodes, mapping)
    network = overlay_network
    display_triangle_inequality_satisfaction(network)

    # Special visualization for the underlay-overlay network:
    # -------------------------------------------------------------------
    united_network = nx.compose(underlay_network, overlay_network)
    used_nodes = set(overlay_network.nodes)
    logical_links = set(overlay_network.edges)
    physical_links = set(underlay_network.edges)
    save_plot("./overlay.png", basemap_plot_network(united_network, used_nodes, logical_links, set(), "red"))
    save_plot("./underlay.png", basemap_plot_network(united_network, used_nodes, physical_links, set(), "orange"))
