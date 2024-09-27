import itertools
import networkx as nx

from plot import basemap_plot_network, save_plot
from overlay_underlay import create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping
from solver import MultiTrackOptimizerType, SingleTrackOptimizerType, get_multi_track_optimizer, get_single_track_optimizer
from model import default_calculate_latency
from traffic import choose_peers, generate_broadcast_traffic, generate_point_of_presence_relays

MAGIC_SEED = 69


def generate_isles(number_of_isles: int, nodes_per_isle: int) -> nx.DiGraph:
    isles: list[nx.DiGraph] = []
    for i in range(number_of_isles):
        isle: nx.DiGraph = nx.complete_graph(map(lambda j: f"isle{i}_node{j}", range(nodes_per_isle)), nx.DiGraph())
        isles.append(isle)
    
    graph_of_isles: nx.DiGraph = nx.compose_all(isles)

    # Set intra isle costs
    for u, v in graph_of_isles.edges:
        graph_of_isles.edges[u, v]["cost"] = graph_of_isles.edges[v, u]["cost"] = 1

    # Set inter isle costs (and add those links beforehand)
    for isle1, isle2 in itertools.combinations(isles, 2):
        node1, node2 = list(isle1.nodes)[0], list(isle2.nodes)[0]
        graph_of_isles.add_edge(node1, node2, cost=nodes_per_isle)
        graph_of_isles.add_edge(node2, node1, cost=nodes_per_isle)

    pos = nx.spring_layout(graph_of_isles, seed=MAGIC_SEED)
    for node, (lat, lon) in pos.items():
        graph_of_isles.nodes[node]["location"] = (float(lat), float(lon))

    # Set latency values to all (both inter and intra isle) edges
    for u, v in graph_of_isles.edges:
        graph_of_isles.edges[u, v]["latency"] = graph_of_isles.edges[v, u]["latency"] = default_calculate_latency(graph_of_isles, u, v)

    return graph_of_isles


if __name__ == "__main__":
    number_of_isles, nodes_per_isle = 2, 4

    base_network = generate_isles(number_of_isles, nodes_per_isle)
    # cdn_nodes = generate_circle_edge_relays(base_network, number_of_isles * 2)
    cdn_nodes = generate_point_of_presence_relays(base_network)
    
    underlay_network = create_underlay_network(base_network, cdn_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, cdn_nodes)
    overlay_network = create_overlay_network(underlay_network, cdn_nodes, mapping)
    network = overlay_network

    track_id = "live"
    publisher, *subscribers = choose_peers(network, number_of_isles * 2, seed=MAGIC_SEED)
    tracks = generate_broadcast_traffic(track_id, publisher, subscribers, 8)

    single_track_optimizer = get_single_track_optimizer(SingleTrackOptimizerType.MULTICAST_HEURISTIC)
    multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizerType.ADAPTED, single_track_optimizer=single_track_optimizer)

    success, objective, avg_delay, used_links_per_track = multi_track_optimizer(network, tracks)

    print(f"Optimization {"succeeded" if success else "failed"}:")
    print(f"\tTotal cost of network: {objective:.2f} USD")
    print(f"\tAverage delay in network: {avg_delay:.2f} ms")

    united_network = nx.compose(underlay_network, overlay_network)
    used_nodes = set(overlay_network.nodes)
    logical_links = set(overlay_network.edges)
    used_logical_links = set(used_links_per_track[track_id])
    physical_links = set(underlay_network.edges)
    used_physical_links = set(itertools.chain.from_iterable(map(lambda logical_link: mapping[logical_link], used_logical_links)))
    save_plot("./overlay.png", basemap_plot_network(united_network, used_nodes, logical_links, used_logical_links, "red"))
    save_plot("./underlay.png", basemap_plot_network(united_network, used_nodes, physical_links, used_physical_links, "orange"))
