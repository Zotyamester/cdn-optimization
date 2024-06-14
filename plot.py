from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from model import Network, Track


def plot_network(network: Network, tracks: dict[str, Track], track_to_color: dict[str, str], used_links_per_track: dict[str, list[tuple[str, str]]]):
    g = nx.DiGraph()

    for node, (location, cost_factor) in network.nodes.items():
        g.add_node(node, location=location, cost_factor=cost_factor)
    for link, (latency, cost) in network.links.items():
        g.add_edge(*link, latency=latency, cost=cost)

    node_positions = {node_name: (node_attrs["location"][1], node_attrs["location"][0])
                      for node_name, node_attrs in g.nodes.data()}

    plt.figure(figsize=(16, 10))
    nx.draw_networkx(g, pos=node_positions, node_size=4000,
                     font_size=10, font_color="white", arrowstyle="-")

    for track, used_links in used_links_per_track.items():
        nx.draw_networkx_edges(g, pos=node_positions,
                               edgelist=used_links, edge_color=track_to_color[track], width=3, arrowsize=15, node_size=3800)

    plt.axis("off")
    plt.show()
