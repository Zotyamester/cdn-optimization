import json
import hashlib
import os
from model import Network, Node, display_network_links, display_track_stats
from plot import get_plotter
from solver import get_multi_track_optimizer
from argparse import ArgumentParser
from traffic import generate_live_video_traffic, generate_video_conference_traffic

CACHE_DIR = "./cache"

nodes = {
    # European nodes
    "eu-west-1":    Node((53.3498, -6.2603), 1.08),     # Dublin, IE
    "eu-west-2":    Node((51.5074, -0.1278), 1.26),     # London, GB
    "eu-west-3":    Node((48.8566, 2.3522), 1.08),      # Paris, FR
    "eu-central-1": Node((50.1109, 8.6821), 1.08),      # Frankfurt, DE
    "eu-north-1":   Node((59.3293, 18.0686), 0.094),    # Stockholm, SE
    "eu-south-1":   Node((45.4642, 9.1900), 1.08),      # Milan, IT
    "Aalborg":      Node((57.0169, 9.9891), 0.15),      # Aalborg, DK
    "Budapest":     Node((47.4732, 19.0379), 0.012),    # Budapest, HU

    # Other nodes
    "us-east-1":    Node((39.0481, -77.4729), 1.08),    # Northern Virginia, US
    "us-west-1":    Node((37.7749, -122.4194), 1.08),   # San Francisco, US
    "us-west-2":    Node((45.5231, -122.6765), 1.08),   # Oregon, US
}

# TODO: Oh boy, this is terrible...
link_costs = {
    ("eu-west-1", "eu-west-2"): 0.02,  # Dublin to London
    ("eu-west-1", "eu-west-3"): 0.03,  # Dublin to Paris
    ("eu-west-1", "eu-central-1"): 0.04,  # Dublin to Frankfurt
    ("eu-west-1", "eu-north-1"): 0.05,  # Dublin to Stockholm
    ("eu-west-1", "eu-south-1"): 0.06,  # Dublin to Milan
    ("eu-west-1", "Aalborg"): 0.07,  # Dublin to Aalborg
    ("eu-west-1", "Budapest"): 0.08,  # Dublin to Budapest
    ("eu-west-1", "us-east-1"): 0.09,  # Dublin to Northern Virginia
    ("eu-west-1", "us-west-1"): 0.10,  # Dublin to San Francisco
    ("eu-west-1", "us-west-2"): 0.11,  # Dublin to Oregon

    ("eu-west-2", "eu-west-3"): 0.02,  # London to Paris
    ("eu-west-2", "eu-central-1"): 0.03,  # London to Frankfurt
    ("eu-west-2", "eu-north-1"): 0.04,  # London to Stockholm
    ("eu-west-2", "eu-south-1"): 0.05,  # London to Milan
    ("eu-west-2", "Aalborg"): 0.06,  # London to Aalborg
    ("eu-west-2", "Budapest"): 0.07,  # London to Budapest
    ("eu-west-2", "us-east-1"): 0.08,  # London to Northern Virginia
    ("eu-west-2", "us-west-1"): 0.09,  # London to San Francisco
    ("eu-west-2", "us-west-2"): 0.10,  # London to Oregon

    ("eu-west-3", "eu-central-1"): 0.02,  # Paris to Frankfurt
    ("eu-west-3", "eu-north-1"): 0.03,  # Paris to Stockholm
    ("eu-west-3", "eu-south-1"): 0.04,  # Paris to Milan
    ("eu-west-3", "Aalborg"): 0.05,  # Paris to Aalborg
    ("eu-west-3", "Budapest"): 0.06,  # Paris to Budapest
    ("eu-west-3", "us-east-1"): 0.07,  # Paris to Northern Virginia
    ("eu-west-3", "us-west-1"): 0.08,  # Paris to San Francisco
    ("eu-west-3", "us-west-2"): 0.09,  # Paris to Oregon

    ("eu-central-1", "eu-north-1"): 0.02,  # Frankfurt to Stockholm
    ("eu-central-1", "eu-south-1"): 0.03,  # Frankfurt to Milan
    ("eu-central-1", "Aalborg"): 0.04,  # Frankfurt to Aalborg
    ("eu-central-1", "Budapest"): 0.05,  # Frankfurt to Budapest
    ("eu-central-1", "us-east-1"): 0.06,  # Frankfurt to Northern Virginia
    ("eu-central-1", "us-west-1"): 0.07,  # Frankfurt to San Francisco
    ("eu-central-1", "us-west-2"): 0.08,  # Frankfurt to Oregon

    ("eu-north-1", "eu-south-1"): 0.02,  # Stockholm to Milan
    ("eu-north-1", "Aalborg"): 0.03,  # Stockholm to Aalborg
    ("eu-north-1", "Budapest"): 0.04,  # Stockholm to Budapest
    ("eu-north-1", "us-east-1"): 0.05,  # Stockholm to Northern Virginia
    ("eu-north-1", "us-west-1"): 0.06,  # Stockholm to San Francisco
    ("eu-north-1", "us-west-2"): 0.07,  # Stockholm to Oregon

    ("eu-south-1", "Aalborg"): 0.02,  # Milan to Aalborg
    ("eu-south-1", "Budapest"): 0.03,  # Milan to Budapest
    ("eu-south-1", "us-east-1"): 0.04,  # Milan to Northern Virginia
    ("eu-south-1", "us-west-1"): 0.05,  # Milan to San Francisco
    ("eu-south-1", "us-west-2"): 0.06,  # Milan to Oregon

    ("Aalborg", "Budapest"): 0.02,  # Aalborg to Budapest
    ("Aalborg", "us-east-1"): 0.03,  # Aalborg to Northern Virginia
    ("Aalborg", "us-west-1"): 0.04,  # Aalborg to San Francisco
    ("Aalborg", "us-west-2"): 0.05,  # Aalborg to Oregon

    ("Budapest", "us-east-1"): 0.02,  # Budapest to Northern Virginia
    ("Budapest", "us-west-1"): 0.03,  # Budapest to San Francisco
    ("Budapest", "us-west-2"): 0.04,  # Budapest to Oregon

    ("us-east-1", "us-west-1"): 0.02,  # Northern Virginia to San Francisco
    ("us-east-1", "us-west-2"): 0.03,  # Northern Virginia to Oregon

    ("us-west-1", "us-west-2"): 0.02,  # San Francisco to Oregon
}


def calculate_cost(_, node1, node2):
    global link_costs
    link = (node1, node2)
    if link in link_costs:
        return link_costs[link]
    reverse_link = (node2, node1)
    if reverse_link in link_costs:
        return link_costs[reverse_link]
    raise ValueError(f"Link cost not found for {link} or {reverse_link}")


COLORS = ["red", "blue", "green", "yellow", "purple", "orange", "pink"]


def hash_input_model(network: Network, tracks: dict[str, list[str]]) -> str:
    base_str = str(network) + str(tracks)
    hash_data = hashlib.sha256(base_str.encode())
    return hash_data.hexdigest()


def optimize(network: Network, tracks: dict[str, list[str]], solver_type: str, debug: bool) -> dict[str, list[tuple[str, str]]]:
    multi_track_optimizer = get_multi_track_optimizer(solver_type)

    status, used_links_per_track = multi_track_optimizer(
        network, tracks, debug)

    if debug:
        status_message = "succeeded" if status else "failed"
        print(f"Optimization {status_message}.")

    return used_links_per_track


if __name__ == "__main__":
    parser = ArgumentParser(
        description="MoQ Relay Topology Optimization with ILP")
    parser.add_argument("--traffic-type",
                        choices=["live", "video-conference"], default="live", help="Type of traffic to generate")
    parser.add_argument("--use-cache",
                        action="store_true", default=True, help="Cache the results (using the input data as a key)")
    parser.add_argument("--solver",
                        choices=["single", "multiple"], default="single", help="Solver to use")
    parser.add_argument("--debug",
                        action="store_true", default=False, help="Debug mode")
    parser.add_argument("--plotter",
                        choices=["simple", "basemap"], default="basemap", help="Plotter to use")
    args = parser.parse_args()

    network = Network(nodes, calculate_cost)
    if args.debug:
        display_network_links(network)

    tracks = generate_live_video_traffic() if args.traffic_type == "live" else generate_video_conference_traffic([
        "Budapest", "Aalborg", "us-west-1", "us-west-2", "eu-central-1"])
    if args.debug:
        display_track_stats(nodes, tracks)

    used_links_per_track = {}

    if args.use_cache:
        input_model_hash = hash_input_model(network, tracks)
        cache_filename = f"{CACHE_DIR}/{input_model_hash}.json"

        try:
            # Read cached data if available
            with open(cache_filename, "r") as f:
                used_links_per_track = json.load(f)

            print("Using cached data...")

            # Transformation needed, since JSON makes tuples indistinguishable from lists
            for links in used_links_per_track.values():
                for i, link in enumerate(links):
                    links[i] = tuple(link)
        except FileNotFoundError:
            print("Not cached yet, computing...")

            used_links_per_track = optimize(
                network, tracks, args.solver, args.debug)

            # Cache the results
            if not os.path.exists(CACHE_DIR):
                os.mkdir(CACHE_DIR)
            with open(cache_filename, "w") as f:
                json.dump(used_links_per_track, f)
    else:
        print("Computing...")
        used_links_per_track = optimize(
            network, tracks, args.solver, args.debug)

    track_to_color = {track_id: color for track_id,
                      color in zip(tracks.keys(), COLORS)}

    plotter = get_plotter(args.plotter)
    plotter(network, tracks, track_to_color, used_links_per_track)
