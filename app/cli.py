import hashlib
import json
import os
from random import randint, seed
import time
from argparse import ArgumentParser

import networkx as nx

from model import Track, display_network_links, display_tracks_stats
from plot import PlotterType, get_plotter, save_plot
from sample import load_network
from solver import MultiTrackOptimizerType, SingleTrackOptimizerType, get_multi_track_optimizer, get_single_track_optimizer
from traffic import choose_peers, generate_broadcast_traffic, generate_full_mesh_traffic

CACHE_DIR = "./cache"
PLOT_DIR = "./plots"


def hash_input_model(network: nx.DiGraph, tracks: dict[str, Track]) -> str:
    base_str = str(network.nodes(data=True)) + \
        str(network.edges(data=True)) + str(tracks)
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


def get_optimal_topology(network: nx.DiGraph, tracks: dict[str, Track], use_cache: bool = False,
                         single_track_optimizer_type: SingleTrackOptimizerType = SingleTrackOptimizerType.INTEGER_LINEAR_PROGRAMMING,
                         multi_track_optimizer_type: MultiTrackOptimizerType = MultiTrackOptimizerType.ADAPTED,
                         debug: bool = False) -> dict[str, list[tuple[str, str]]]:
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

        single_track_optimizer = get_single_track_optimizer(
            single_track_optimizer_type)
        multi_track_optimizer = get_multi_track_optimizer(
            multi_track_optimizer_type, single_track_optimizer=single_track_optimizer)

        success, objective, avg_delay, used_links_per_track = multi_track_optimizer(
            network, tracks)

        if debug:
            print(f"Optimization {"succeeded" if success else "failed"}:")
            print(f"\tTotal cost of network: {objective:.2f} USD")
            print(f"\tAverage delay in network: {avg_delay:.2f} ms")
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
        track_id = "live"
        publisher, *subscribers = peers
        return generate_broadcast_traffic(track_id, publisher, subscribers, 150)
    elif type == "video-conference":
        return generate_full_mesh_traffic(peers, 200)
    else:
        raise ValueError(f"Unknown traffic type: {type}")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="MoQ Relay Topology Optimization")
    parser.add_argument("--network", default="small_topo.yaml",
                        help="Network topology file")
    parser.add_argument("--traffic-type",
                        choices=["live", "video-conference"], default="live", help="Type of traffic to generate")
    parser.add_argument("--peers", nargs="+", default=["virginia", "lenoir", "ohio", "dublin", "middenmeer", "belgium"],
                        help="Peers to generate traffic for")
    parser.add_argument("--use-cache",
                        action="store_true", default=False, help="Cache the results (using the input data as a key)")
    parser.add_argument("--single-track-optimizer",
                        choices=[opt.name for opt in SingleTrackOptimizerType], default=SingleTrackOptimizerType.MULTICAST_HEURISTIC.name,
                        help="Single track optimizer to use (ignored if multi-track optimizer is not set to ADAPTED)")
    parser.add_argument("--multi-track-optimizer",
                        choices=[opt.name for opt in MultiTrackOptimizerType], default=MultiTrackOptimizerType.ADAPTED.name, help="Multi track optimizer to use")
    parser.add_argument("--debug",
                        action="store_true", default=True, help="Debug mode")
    parser.add_argument("--plotter", choices=[opt.name for opt in PlotterType],
                        default=PlotterType.BASEMAP.name, help="Plotter to use")
    parser.add_argument("--plot-name", default="plot",
                        help="Name of the plot file (without extension)")
    args = parser.parse_args()

    topology_filename = os.path.join(
        "datasource", os.path.basename("small_topo.yaml"))
    network = load_network(topology_filename)

    seed(42)
    peers = args.peers if len(args.peers) >= 2 else choose_peers(
        network, randint(5, len(network.nodes)))
    tracks = generate_sample_traffic(args.traffic_type, peers)

    if args.debug:
        display_network_links(network)
        display_tracks_stats(tracks)

    start = time.time()
    used_links_per_track = get_optimal_topology(
        network, tracks, args.use_cache,
        SingleTrackOptimizerType[args.single_track_optimizer],
        MultiTrackOptimizerType[args.multi_track_optimizer],
        args.debug
    )
    end = time.time()

    delta = end - start
    if args.debug:
        print(f"Computation time: {delta:.4f} s")

    if not os.path.exists(PLOT_DIR):
        os.mkdir(PLOT_DIR)

    plotter = get_plotter(PlotterType[args.plotter])
    for track_id, used_links in used_links_per_track.items():
        image_bytes = plotter(network, set(network.nodes), set(
            network.edges), set(used_links), "red")
        filename = f"{PLOT_DIR}/{args.plot_name}-{track_id}.png"
        if args.debug:
            print(f"Saving plot to {filename}")
        save_plot(filename, image_bytes)
