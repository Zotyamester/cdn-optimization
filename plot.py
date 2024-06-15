from typing import Callable
from model import Network, Track
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt


def basemap_plot_network(network: Network, tracks: dict[str, Track], track_to_color: dict[str, str], used_links_per_track: dict[str, list[tuple[str, str]]]):
    m = Basemap(resolution='c', projection='merc', llcrnrlon=-
                15, llcrnrlat=35, urcrnrlon=30, urcrnrlat=70)

    plt.figure(figsize=(10, 12))
    m.fillcontinents(color='lightgray', lake_color='white')

    node_positions = {node: (location[1], location[0])
                      for node, (location, _) in network.nodes.items()}

    link_to_tracks = {}
    for track, used_links in used_links_per_track.items():
        for link in used_links:
            if link not in link_to_tracks:
                link_to_tracks[link] = []
            link_to_tracks[link].append(track)

    # Plot links
    for link in network.links.keys():
        lon1, lat1 = node_positions[link[0]]
        lon2, lat2 = node_positions[link[1]]
        x1, y1 = m(lon1, lat1)
        x2, y2 = m(lon2, lat2)

        if link not in link_to_tracks:
            plt.plot([x1, x2], [y1, y2], color='gray', linewidth=1)
        else:
            tracks = link_to_tracks[link]
            dx, dy = (x2 - x1) / len(tracks), (y2 - y1) / len(tracks)
            for i, track in enumerate(tracks):
                plt.plot([x1 + i * dx, x1 + (i + 1) * dx], [y1 + i * dy, y1 +
                         (i + 1) * dy], color=track_to_color[track], linewidth=3)

    # Plot nodes
    for node, (lon, lat) in node_positions.items():
        x, y = m(lon, lat)
        m.plot(x, y, 'bo', markersize=10)
        plt.text(x, y, node, fontsize=12, ha='right',
                 va='bottom', color='black')

    plt.show()


def get_plotter(type: str) -> Callable[[Network, dict[str, Track], dict[str, str], dict[str, list[tuple[str, str]]]], None]:
    if type == "basemap":
        return basemap_plot_network
    else:
        raise ValueError(f"Unknown plotter type: {type}")
