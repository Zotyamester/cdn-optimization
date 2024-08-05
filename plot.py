import itertools
from typing import Callable

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
from mpl_toolkits.basemap import Basemap

from model import Track

# This is needed to avoid a runtime error when running on a server
matplotlib.use("Agg")


def simple_plot_network(network: nx.DiGraph, tracks: dict[str, Track], track_to_color: dict[str, str], used_links_per_track: dict[str, list[tuple[str, str]]], filename: str):
    node_positions = {node_name: (node_attrs["location"][1], node_attrs["location"][0])
                      for node_name, node_attrs in network.nodes.data()}

    plt.figure(figsize=(16, 10))
    nx.draw_networkx(network, pos=node_positions, node_size=2000,
                     font_size=8, font_color="white", arrowstyle="-")

    for track, used_links in used_links_per_track.items():
        nx.draw_networkx_edges(network, pos=node_positions,
                               edgelist=used_links, edge_color=track_to_color[track], width=3, arrowsize=15, node_size=1900)

    plt.axis("off")
    plt.savefig(filename)
    plt.close()


def basemap_plot_network(network: nx.DiGraph, tracks: dict[str, Track], track_to_color: dict[str, str], used_links_per_track: dict[str, list[tuple[str, str]]], filename: str):
    min_lon = 90
    max_lon = -90
    min_lat = 180
    max_lat = -180

    node_positions = {}
    for node, data in network.nodes.items():
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

    link_to_tracks = {}
    for track, used_links in used_links_per_track.items():
        for link in used_links:
            if link not in link_to_tracks:
                link_to_tracks[link] = []
            link_to_tracks[link].append(track)

    # Plot links
    for node1, node2 in itertools.combinations(network.nodes.keys(), 2):
        link = (node1, node2)
        reverse_link = (node2, node1)
        lon1, lat1 = node_positions[node1]
        lon2, lat2 = node_positions[node2]
        x1, y1 = m(lon1, lat1)
        x2, y2 = m(lon2, lat2)

        if link not in link_to_tracks and reverse_link not in link_to_tracks:
            plt.plot([x1, x2], [y1, y2], color="gray", linewidth=0.1)
        else:
            tracks_on_link, tracks_on_reverse_link = link_to_tracks.get(
                link, []), link_to_tracks.get(reverse_link, [])
            count = len(tracks_on_link) + len(tracks_on_reverse_link)
            dx, dy = (x2 - x1) / count, (y2 - y1) / count
            plot_track_arrows(x1, y1, dx, dy, tracks_on_link, track_to_color)
            plot_track_arrows(x2, y2,
                              -dx, -dy, tracks_on_reverse_link, track_to_color)

    # Plot nodes
    for node, (lon, lat) in node_positions.items():
        x, y = m(lon, lat)
        m.plot(x, y, "bo", markersize=6)
        plt.text(x, y, node, fontsize=12, ha="right",
                 va="bottom", color="black")

    plt.savefig(filename)
    plt.close()


def plot_track_arrows(x1, y1, dx, dy, tracks_on_link, track_to_color):
    for i, track in enumerate(tracks_on_link):
        plt.arrow(x1 + i * dx, y1 + i * dy, dx, dy,
                  color=track_to_color[track], linewidth=2, head_width=0.5, head_length=0.2, length_includes_head=True)


def get_plotter(type: str) -> Callable[[nx.DiGraph, dict[str, Track], dict[str, str], dict[str, list[tuple[str, str]]], str], None]:
    if type == "simple":
        return simple_plot_network
    elif type == "basemap":
        return basemap_plot_network
    else:
        raise ValueError(f"Unknown plotter type: {type}")
