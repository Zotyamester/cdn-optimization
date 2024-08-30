import math
from pathlib import Path
from typing import Callable
import geopy.distance
import matplotlib.pyplot as plt
import networkx as nx
from mpl_toolkits.basemap import Basemap
from model import default_calculate_latency, default_calculate_cost, display_triangle_inequality_satisfaction, load_graphml


cdn_nodes = [
    # European nodes
    ("eu-west-1",    {"location": (53.3498, -6.2603)}),    # Dublin, IE
    ("eu-west-2",    {"location": (51.5074, -0.1278)}),    # London, GB
    ("eu-west-3",    {"location": (48.8566, 2.3522)}),     # Paris, FR
    ("eu-central-1", {"location": (50.1109, 8.6821)}),     # Frankfurt, DE
    ("eu-north-1",   {"location": (59.3293, 18.0686)}),    # Stockholm, SE
    ("eu-south-1",   {"location": (45.4642, 9.1900)}),     # Milan, IT
    # American nodes
    ("us-east-1",    {"location": (39.0481, -77.4729)}),   # Northern Virginia, US
    ("us-west-1",    {"location": (37.7749, -122.4194)}),  # San Francisco, US
    ("us-west-2",    {"location": (45.5231, -122.6765)}),  # Oregon, US
]


def find_closest_node(graph: nx.DiGraph, cdn_node_data: dict) -> str:
    closest_node = None
    distance = math.inf
    for node, node_data in graph.nodes(data=True):
        node_distance = geopy.distance.geodesic(
            cdn_node_data["location"], node_data["location"]).km
        if node_distance < distance:
            closest_node = node
            distance = node_distance
    return closest_node


def load_base_network(base_network_path: str,
                      calculate_latency: Callable[[nx.DiGraph, str, str], float] = default_calculate_latency,
                      calculate_cost: Callable[[nx.DiGraph, str, str], float] = default_calculate_cost) -> nx.DiGraph:
    base_network = load_graphml(base_network_path, calculate_latency, calculate_cost)

    # Prefix node names with base filename (without extension)
    common_node_name_prefix = Path(base_network_path).stem.lower() + "_"
    nx.relabel_nodes(base_network, {node: common_node_name_prefix + node for node in base_network.nodes}, False)

    return base_network


def create_underlay_network(base: nx.DiGraph,
                            cdn_nodes: list[tuple[str, dict]],
                            calculate_latency: Callable[[nx.DiGraph, str, str], float] = default_calculate_latency) -> nx.DiGraph:
    underlay = base.copy()  # Make a copy for several reasons, one of which is that the base network is used for selecting the connection point for the actual CDN

    # Connect the nodes of the CDN to the closest node of the base network with zero cost (the cost of access is neglegible for us)
    for cdn_node, cdn_node_data in cdn_nodes:
        closest_node = find_closest_node(base, cdn_node_data)
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


def basemap_plot_network(network: nx.DiGraph, logical_links: set[tuple[str, str]], physical_links: set[tuple[str, str]]):
    min_lon = 90
    max_lon = -90
    min_lat = 180
    max_lat = -180

    node_positions = {}
    for node, data in network.nodes(data=True):
        location = data["location"]
        lon, lat = location[1], location[0]
        node_positions[node] = (lon, lat)

        if lon < min_lon:
            min_lon = lon
        elif lon > max_lon:
            max_lon = lon

        if lat < min_lat:
            min_lat = lat
        elif lat > max_lat:
            max_lat = lat

    min_lon = max(min_lon - abs(min_lon) * 0.2, -180)
    max_lon = min(max_lon + abs(max_lon) * 0.2, 180)
    min_lat = max(min_lat - abs(min_lat) * 0.2, -90)
    max_lat = min(max_lat + abs(max_lat) * 0.2, 90)

    m = Basemap(resolution="c", projection="merc",
                llcrnrlon=min_lon, llcrnrlat=min_lat, urcrnrlon=max_lon, urcrnrlat=max_lat)

    plt.figure(figsize=(16, 9))
    m.fillcontinents(color="lightgray", lake_color="white")

    # Plot links
    for node1, node2, data in network.edges(data=True):
        lon1, lat1 = node_positions[node1]
        lon2, lat2 = node_positions[node2]
        x1, y1 = m(lon1, lat1)
        x2, y2 = m(lon2, lat2)

        link = (node1, node2)
        if link in logical_links:
            plt.plot([x1, x2], [y1, y2], color="red", linewidth=0.3)
        elif link in physical_links:
            plt.plot([x1, x2], [y1, y2], color="orange", linewidth=0.2)
        else:
            plt.plot([x1, x2], [y1, y2], color="black", linewidth=0.1)

    # Plot nodes
    for node, (lon, lat) in node_positions.items():
        x, y = m(lon, lat)
        if node in [cdn_node for cdn_node, _ in cdn_nodes]:
            m.plot(x, y, "ro", markersize=2)
        else:
            m.plot(x, y, "bo", markersize=2)

    plt.savefig("./plots/plot.png")
    plt.close()


base_network = load_base_network("./datasource/Cogentco.graphml")
underlay_network = create_underlay_network(base_network, cdn_nodes)
mapping = create_virtual_to_physical_mapping(underlay_network, cdn_nodes)
overlay_network = create_overlay_network(underlay_network, cdn_nodes, mapping)

# To remain compatible with the other samples provided.
network = overlay_network

if __name__ == "__main__":
    display_triangle_inequality_satisfaction(network)

    # Special visualization for the underlay-overlay network:
    # -------------------------------------------------------------------
    # united_network = nx.compose(underlay_network, overlay_network)
    # logical_links = set(mapping.keys())
    # physical_links = set(chain.from_iterable(mapping.values()))
    # basemap_plot_network(united_network, logical_links, physical_links)
