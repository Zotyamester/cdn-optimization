import itertools
from typing import Callable

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
from mpl_toolkits.basemap import Basemap

from model import Track

# This is needed to avoid a runtime error when running on a server
matplotlib.use("Agg")


def simple_plot_network(network: nx.DiGraph,
                        _1: set[str],
                        _2: set[tuple[str, str]], used_links: set[tuple[str, str]],
                        color: str,
                        filename: str):
    node_positions = {node_name: (node_attrs["location"][1], node_attrs["location"][0])
                      for node_name, node_attrs in network.nodes.data()}

    plt.figure(figsize=(25, 15))
    nx.draw_networkx(network, pos=node_positions, node_size=2200,
                     font_size=6, font_color="white", arrowstyle="-")

    for used_links in used_links:
        nx.draw_networkx_edges(network, pos=node_positions,
                               edgelist=used_links, edge_color=color, width=3, arrowsize=15, node_size=2100)

    plt.axis("off")
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
    plt.close()


def basemap_plot_network(network: nx.DiGraph,
                         used_nodes: set[str],
                         shown_links: set[tuple[str, str]], used_links: set[tuple[str, str]],
                         color: str,
                         filename: str):
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

    min_lon = max(min_lon - abs(min_lon) * 0.25, -180)
    max_lon = min(max_lon + abs(max_lon) * 0.25, 180)
    min_lat = max(min_lat - abs(min_lat) * 0.25, -90)
    max_lat = min(max_lat + abs(max_lat) * 0.25, 90)

    m = Basemap(resolution="c", projection="merc",
                llcrnrlon=min_lon, llcrnrlat=min_lat, urcrnrlon=max_lon, urcrnrlat=max_lat)

    plt.figure(figsize=(25, 15))
    m.fillcontinents(color="lightgray", lake_color="white")

    # Plot links
    for node1, node2 in network.edges:
        link = (node1, node2)
        if link not in shown_links:
            continue

        lon1, lat1 = node_positions[node1]
        lon2, lat2 = node_positions[node2]
        x1, y1 = m(lon1, lat1)
        x2, y2 = m(lon2, lat2)

        if link in used_links:
            plt.plot([x1, x2], [y1, y2], color=color, linewidth=1.0)
        else:
            plt.plot([x1, x2], [y1, y2], color="gray", linewidth=0.08)

    # Plot nodes
    for node, (lon, lat) in node_positions.items():
        x, y = m(lon, lat)

        if node in used_nodes:
            m.plot(x, y, "bo", markersize=3.2)
            plt.text(x, y, node, fontsize=12, ha="right", va="bottom", color="black")
        else:
            m.plot(x, y, "ks", markersize=1.6)

    plt.axis("off")
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
    plt.close()


def get_plotter(type: str) -> Callable[[nx.DiGraph, set[str], set[tuple[str, str]], set[tuple[str, str]], str, str], None]:
    if type == "simple":
        return simple_plot_network
    elif type == "basemap":
        return basemap_plot_network
    else:
        raise ValueError(f"Unknown plotter type: {type}")
