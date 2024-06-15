from model import Network, Node, Track, display_network_links, display_track_stats
from plot import get_plotter, plot_network
from solver import get_optimal_topology
import pulp as lp

# Sample network, track and plot configuration *******************************************************************

nodes = {
    "eu-west-1":    Node((53.3498, -6.2603), 1.08),     # Dublin, IE
    "eu-west-2":    Node((51.5074, -0.1278), 1.26),     # London, GB
    "eu-west-3":    Node((48.8566, 2.3522), 1.08),      # Paris, FR
    "eu-central-1": Node((50.1109, 8.6821), 1.08),      # Frankfurt, DE
    "eu-north-1":   Node((59.3293, 18.0686), 0.094),    # Stockholm, SE
    "eu-south-1":   Node((45.4642, 9.1900), 1.08),      # Milan, IT
    "Aalborg":      Node((57.0169, 9.9891), 0.15),      # Aalborg, DK
    "Budapest":     Node((47.4732, 19.0379), 0.0029)    # Budapest, HU
}

network = Network(nodes)
display_network_links(network)

tracks = {
    "t1": Track(
        name="Gajdos Összes Rövidítve",
        publisher="eu-central-1",
        subscribers=[
            ("Budapest", 95),
            ("Aalborg", 5),
            ("eu-north-1", 16),
            ("eu-south-1", 10),
        ]
    ),
    "t2": Track(
        name="Szirmay - A halálosztó",
        publisher="eu-south-1",
        subscribers=[
            ("Budapest", 50),
            ("Budapest", 30),
            ("Aalborg", 10),
            ("eu-north-1", 70),
        ]
    ),
}
display_track_stats(nodes, tracks)

track_to_color = {
    "t1": "red",
    "t2": "blue",
}

# Optimize network ***********************************************************************************************

used_links_per_track = {}
for track_id, track in tracks.items():
    print(f"Optimizing network for track {track_id}...")
    status, used_links = get_optimal_topology(network, track, debug=True)
    if status == lp.const.LpStatusOptimal:
        print(f"Optimization successful for track {track_id}")
        used_links_per_track[track_id] = used_links
    else:
        print(f"Optimization failed for track {track_id}")
    print()

# Plot the network ***********************************************************************************************

plotter = get_plotter("basemap")
plotter(network, tracks, track_to_color, used_links_per_track)
