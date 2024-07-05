import hashlib
import json
import os
from argparse import ArgumentParser
import pulp as lp

from sample import network
from model import Network, Track, display_network_links, display_track_stats
from plot import get_plotter
from solver import get_multi_track_optimizer
from traffic import (generate_live_video_traffic,
                     generate_video_conference_traffic)

CACHE_DIR = "./cache"
PLOT_DIR = "./plots"


COLORS = ["red", "blue", "green", "yellow",
          "purple", "orange", "pink", "brown"]


def hash_input_model(network: Network, tracks: dict[str, list[str]]) -> str:
    base_str = str(network) + str(tracks)
    hash_data = hashlib.sha256(base_str.encode())
    return hash_data.hexdigest()


def is_cached(input_model_hash: str) -> bool:
    return os.path.exists(f"{CACHE_DIR}/{input_model_hash}.json")


def read_from_cache(input_model_hash: str) -> dict[str, list[tuple[str, str]]]:
    with open(f"{CACHE_DIR}/{input_model_hash}.json", "r") as f:
        return json.load(f)


def write_to_cache(input_model_hash: str, used_links_per_track: dict[str, list[tuple[str, str]]]):
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)
    with open(f"{CACHE_DIR}/{input_model_hash}.json", "w") as f:
        json.dump(used_links_per_track, f)


def get_optimal_topology(network: Network, tracks: dict[str, Track], solver_type: str, use_cache: bool = False, debug: bool = False) -> dict[str, list[tuple[str, str]]]:
    input_model_hash = hash_input_model(network, tracks)

    if use_cache and is_cached(input_model_hash):
        if debug:
            print("Using cached data...")

        used_links_per_track = read_from_cache(input_model_hash)

        # Transformation needed, since JSON makes tuples indistinguishable from lists
        for links in used_links_per_track.values():
            for i, link in enumerate(links):
                links[i] = tuple(link)
    else:
        if debug:
            print("Computing...")

        multi_track_optimizer = get_multi_track_optimizer(solver_type)

        status, used_links_per_track = multi_track_optimizer(
            network, tracks, debug)

        if debug:
            status_message = "succeeded" if status == lp.LpStatusOptimal else "failed"
            print(f"Optimization {status_message}.")

        if use_cache and status == lp.LpStatusOptimal:
            write_to_cache(input_model_hash, used_links_per_track)

    return used_links_per_track


def generate_sample_traffic(type: str) -> dict[str, Track]:
    if type == "live":
        CONTENT_1 = "Gajdos Összes Rövidítve"
        CONTENT_2 = "Szirmay - A halálosztó"

        publishers = [("eu-central-1", [CONTENT_1]),
                      ("eu-south-1", [CONTENT_2])]
        qci_table = [0, 100, 150, 50, 300, 100, 300, 100, 300]
        subscribers = [
            ("Budapest", 1, {CONTENT_1, CONTENT_2}),
            ("Aalborg", 2, {CONTENT_1, CONTENT_2}),
            ("eu-north-1", 3, {CONTENT_1, CONTENT_2}),
            ("eu-south-1", 4, {CONTENT_1}),
            ("us-east-1", 5, {CONTENT_1}),
            ("us-west-1", 6, {CONTENT_1}),
            ("us-west-2", 7, {CONTENT_1}),
        ]

        return generate_live_video_traffic(
            publishers, qci_table, subscribers)
    elif type == "video-conference":
        peers = ["Budapest", "Aalborg", "eu-west-3", "eu-west-2",
                 "eu-north-1", "us-west-1", "us-west-2", "eu-central-1"]
        return generate_video_conference_traffic(peers)
    else:
        raise ValueError(f"Unknown traffic type: {type}")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="MoQ Relay Topology Optimization with ILP")
    parser.add_argument("--traffic-type",
                        choices=["live", "video-conference"], default="video-conference", help="Type of traffic to generate")
    parser.add_argument("--use-cache",
                        action="store_true", default=False, help="Cache the results (using the input data as a key)")
    parser.add_argument("--solver",
                        choices=["single", "multiple"], default="multiple", help="Solver to use")
    parser.add_argument("--debug",
                        action="store_true", default=True, help="Debug mode")
    parser.add_argument("--plotter",
                        choices=["simple", "basemap"], default="basemap", help="Plotter to use")
    args = parser.parse_args()

    tracks = generate_sample_traffic(args.traffic_type)
    if args.debug:
        display_network_links(network)
        display_track_stats(network.nodes, tracks)

    used_links_per_track = get_optimal_topology(
        network, tracks, args.solver, args.use_cache, args.debug)

    track_to_color = {track_id: color for track_id,
                      color in zip(tracks.keys(), COLORS)}
    

    if not os.path.exists(PLOT_DIR):
        os.mkdir(PLOT_DIR)
        
    plotter = get_plotter(args.plotter)
    plotter(network, tracks, track_to_color, used_links_per_track, f"{PLOT_DIR}/{args.traffic_type}.png")
