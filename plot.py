import itertools
from typing import Callable
from model import Network, Track
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import networkx as nx


def simple_plot_network(network: Network, tracks: dict[str, Track], track_to_color: dict[str, str], used_links_per_track: dict[str, list[tuple[str, str]]]):
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


def basemap_plot_network(network: Network, tracks: dict[str, Track], track_to_color: dict[str, str], used_links_per_track: dict[str, list[tuple[str, str]]]):
    min_lon = 90
    max_lon = -90
    min_lat = 180
    max_lat = -180

    node_positions = {}
    for node, (location, _) in network.nodes.items():
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

    min_lon = max(min_lon * 1.1, -180)
    max_lon = min(max_lon * 1.1, 180)
    min_lat = max(min_lat * 1.1, -90)
    max_lat = min(max_lat * 1.1, 90)

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
            tracks_on_link, tracks_on_reverse_link = link_to_tracks.get(link, []), link_to_tracks.get(reverse_link, [])
            count = len(tracks_on_link) + len(tracks_on_reverse_link)
            dx, dy = (x2 - x1) / count, (y2 - y1) / count
            for i, track in enumerate(tracks_on_link):
                plt.arrow(x1 + i * dx, y1 + i * dy, dx, dy,
                          color=track_to_color[track], linewidth=2, head_width=0.5, head_length=0.2)
            for i, track in enumerate(reversed(tracks_on_reverse_link)):
                plt.arrow(x2 - i * dx, y2 - i * dy, -dx, -dy,
                          color=track_to_color[track], linewidth=2, head_width=0.5, head_length=0.2)

    # Plot nodes
    for node, (lon, lat) in node_positions.items():
        x, y = m(lon, lat)
        m.plot(x, y, "bo", markersize=10)
        plt.text(x, y, node, fontsize=12, ha="right",
                 va="bottom", color="black")

    plt.show()


def get_plotter(type: str) -> Callable[[Network, dict[str, Track], dict[str, str], dict[str, list[tuple[str, str]]]], None]:
    if type == "simple":
        return simple_plot_network
    elif type == "basemap":
        return basemap_plot_network
    else:
        raise ValueError(f"Unknown plotter type: {type}")
