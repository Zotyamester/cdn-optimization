import networkx as nx
import matplotlib.pyplot as plt
from model import Network


def plot_network(network: Network, used_links: list[tuple[str, str]]):
    g = nx.Graph()

    for node, (location, cost_factor) in network.nodes.items():
        g.add_node(node, location=location, cost_factor=cost_factor)
    for link, (latency, cost) in network.links.items():
        g.add_edge(*link, latency=latency, cost=cost)

    plt.figure(figsize=(16, 10))
    node_positions = {node_name: (node_attrs["location"][1], node_attrs["location"][0])
                      for node_name, node_attrs in g.nodes.data()}
    nx.draw_networkx(g, pos=node_positions, node_size=4000,
                     font_size=10, font_color="white")
    nx.draw_networkx_edges(g, pos=node_positions,
                           edgelist=used_links, edge_color="red", width=2)

    plt.axis("off")
    plt.show()
