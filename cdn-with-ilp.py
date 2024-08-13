import hashlib
import json
import os
import time
from argparse import ArgumentParser

import networkx as nx

from model import Track, display_network_links, display_tracks_stats
from plot import get_plotter
from sample import network
from solver import MultiTrackOptimizer, SingleTrackOptimizer, get_multi_track_optimizer, get_single_track_optimizer
from traffic import (generate_live_video_traffic,
                     generate_video_conference_traffic)

CACHE_DIR = "./cache"
PLOT_DIR = "./plots"


COLORS = ["red", "blue", "green", "yellow",
          "purple", "orange", "pink", "brown"]


def hash_input_model(network: nx.DiGraph, tracks: dict[str, list[str]]) -> str:
    base_str = str(network.nodes) + str(network.edges(data=True)) + str(tracks)
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


def get_optimal_topology(network: nx.DiGraph, tracks: dict[str, Track], use_cache: bool = False, debug: bool = False) -> dict[str, list[tuple[str, str]]]:
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

        single_track_optimizer = get_single_track_optimizer(SingleTrackOptimizer.INTEGER_LINEAR_PROGRAMMING)
        multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizer.ADAPTED, single_track_optimizer=single_track_optimizer)

        success, objective, used_links_per_track = multi_track_optimizer(
            network, tracks)

        if debug:
            print(f"Optimization {"succeeded" if success else "failed"}:")
            print(f"\tTotal cost of network: {objective:.2f} USD")
            for track, links in used_links_per_track.items():
                print(f"\t{track}: {", ".join(
                    f"{node1} <-> {node2}" for (node1, node2) in links)}")

        if use_cache and success:
            write_to_cache(input_model_hash, used_links_per_track)

    return used_links_per_track


def generate_sample_traffic(type: str, peers: list[str]) -> dict[str, Track]:
    if len(peers) < 2:
        raise ValueError("At least two peers are needed")

    if type == "live":
        CONTENT = "Gajdos Összes Rövidítve"

        publishers = [(peers[0], [CONTENT])]
        subscribers = [(peers[i], CONTENT)
                       for i in range(1, len(peers))]

        return generate_live_video_traffic(publishers, subscribers)
    elif type == "video-conference":
        return generate_video_conference_traffic(peers)
    else:
        raise ValueError(f"Unknown traffic type: {type}")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="MoQ Relay Topology Optimization")
    parser.add_argument("--traffic-type",
                        choices=["live", "video-conference"], default="live", help="Type of traffic to generate")
    parser.add_argument("--peers", nargs="+", default=["us-west1", "us-west2", "us-east1", "europe-south1", "europe-west1", "europe-west2", "europe-west3", "southamerica-east1", "asia-west1", "asia-east1"],
                        help="Peers to generate traffic for")
    parser.add_argument("--use-cache",
                        action="store_true", default=False, help="Cache the results (using the input data as a key)")
    parser.add_argument("--debug",
                        action="store_true", default=True, help="Debug mode")
    parser.add_argument("--plotter",
                        choices=["simple", "basemap"], default="basemap", help="Plotter to use")
    parser.add_argument("--plot-name", default="plot",
                        help="Name of the plot file (without extension)")
    args = parser.parse_args()

    tracks = generate_sample_traffic(args.traffic_type, args.peers)

    if args.debug:
        display_network_links(network)
        display_tracks_stats(tracks)

    start = time.time()
    used_links_per_track = get_optimal_topology(network, tracks, args.use_cache, args.debug)
    end = time.time()

    delta = end - start
    if args.debug:
        print(f"Computation time: {delta:.2f} s")

    track_to_color = {track_id: color for track_id,
                      color in zip(tracks.keys(), COLORS)}

    if not os.path.exists(PLOT_DIR):
        os.mkdir(PLOT_DIR)

    plotter = get_plotter(args.plotter)
    plotter(network, tracks, track_to_color, used_links_per_track,
            f"{PLOT_DIR}/{args.plot_name}.png")
