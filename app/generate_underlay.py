import itertools
import networkx as nx

from plot import simple_plot_network
from calculated_sample import basemap_plot_network, create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping
from solver import MultiTrackOptimizer, SingleTrackOptimizer, get_multi_track_optimizer, get_single_track_optimizer
from model import default_calculate_latency
from traffic import choose_peers, generate_broadcast_traffic, generate_circle_edge_relays


def generate_isles(number_of_isles: int, nodes_per_isle: int) -> nx.DiGraph:
    isles: list[nx.DiGraph] = []
    for i in range(number_of_isles):
        isle: nx.DiGraph = nx.complete_graph(map(lambda j: f"isle{i}_node{j}", range(nodes_per_isle)), nx.DiGraph())
        isles.append(isle)
    
    graph_of_isles: nx.DiGraph = nx.compose_all(isles)

    # Set inter isle costs
    for u, v in graph_of_isles.edges:
        graph_of_isles.edges[u, v]["cost"] = graph_of_isles.edges[v, u]["cost"] = 1

    # Set intra isle costs (and add those links beforehand)
    for isle1, isle2 in itertools.combinations(isles, 2):
        node1, node2 = list(isle1.nodes)[0], list(isle2.nodes)[0]
        graph_of_isles.add_edge(node1, node2, cost=nodes_per_isle)
        graph_of_isles.add_edge(node2, node1, cost=nodes_per_isle)

    pos = nx.spring_layout(graph_of_isles)
    for node, (lat, lon) in pos.items():
        graph_of_isles.nodes[node]["location"] = (float(lat), float(lon))

    # Set latency values to all (both inter and intra isle) edges
    for u, v in graph_of_isles.edges:
        graph_of_isles.edges[u, v]["latency"] = graph_of_isles.edges[v, u]["latency"] = default_calculate_latency(graph_of_isles, u, v)

    return graph_of_isles


if __name__ == "__main__":
    number_of_isles, nodes_per_isle = 4, 5

    base_network = generate_isles(number_of_isles, nodes_per_isle)
    cdn_nodes = generate_circle_edge_relays(base_network, number_of_isles * 2)
    
    underlay_network = create_underlay_network(base_network, cdn_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, cdn_nodes)
    overlay_network = create_overlay_network(underlay_network, cdn_nodes, mapping)
    network = overlay_network

    track_id = "vod"
    publisher, *subscribers = choose_peers(network, number_of_isles + 1, seed=42)
    tracks = generate_broadcast_traffic(track_id, publisher, subscribers, delay_budget=2.4)

    single_track_optimizer = get_single_track_optimizer(SingleTrackOptimizer.MULTICAST_HEURISTIC)
    multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizer.ADAPTED, single_track_optimizer=single_track_optimizer)

    success, objective, used_links_per_track = multi_track_optimizer(network, tracks)

    print(f"Optimization {"succeeded" if success else "failed"}:")
    print(f"\tTotal cost of network: {objective:.2f} USD")

    simple_plot_network(network, tracks, {"vod": "RED"}, used_links_per_track, "test.png")
    
    # united_network = nx.compose(underlay_network, overlay_network)
    # logical_links = set(mapping.keys())
    # physical_links = set(itertools.chain.from_iterable(mapping.values()))
    # basemap_plot_network(united_network, logical_links, physical_links)
