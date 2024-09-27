
from enum import Enum
import time
from typing import IO
from base_network import MAGIC_SEED
from sample import store_network
from model import load_geant_json
from overlay_underlay import create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping, load_base_network
from solver import MultiTrackOptimizerType, MultiTrackSolution, SingleTrackOptimizerType, get_multi_track_optimizer, get_single_track_optimizer
from traffic import choose_peers, generate_broadcast_traffic, generate_continental_relays


class ContentType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    GAMING = "image"
    MESSAGING = "text"


def generate_content(track_id, publisher, subscribers, content_type):
    LATENCIES = {
        ContentType.VIDEO: 400,
        ContentType.AUDIO: 150,
        ContentType.MESSAGING: 1000,
        # ContentType.GAMING: 50,
    }

    tracks = generate_broadcast_traffic(track_id, publisher, subscribers, LATENCIES[content_type])
    return tracks


def benchmark():
    cdn_nodes = generate_continental_relays(7, 10, seed=MAGIC_SEED)

    base_network = load_base_network(load_geant_json("./datasource/geant.json"), "GEANT")
    underlay_network = create_underlay_network(base_network, cdn_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, cdn_nodes)
    overlay_network = create_overlay_network(underlay_network, cdn_nodes, mapping)
    network = overlay_network
    store_network(network, "./datasource/random_benchmark.yaml")

    print("done creating network")

    with open(f"benchmark-{time.strftime('%Y%m%d%H%M%S')}.csv", "wb", buffering=0) as file:
        store_header(file)

        for content_type in ContentType:
            track_id = f"{content_type.name}"

            for number_of_peers in range(2, 4):#len(cdn_nodes) + 1):
                publisher, *subscribers = choose_peers(network, number_of_peers)
                tracks = generate_content(track_id, publisher, subscribers, content_type)

                for single_track_optimizer_type in SingleTrackOptimizerType:
                    single_track_optimizer = get_single_track_optimizer(single_track_optimizer_type)
                    multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizerType.ADAPTED, single_track_optimizer=single_track_optimizer)

                    runtime_in_ms, solution = collect_optimization_info(network, tracks, multi_track_optimizer)
                    store_record(content_type, number_of_peers, single_track_optimizer_type, runtime_in_ms, solution, file)
                
                multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizerType.NATIVE)
                runtime_in_ms, solution = collect_optimization_info(network, tracks, multi_track_optimizer)
                store_record(content_type, number_of_peers, MultiTrackOptimizerType.NATIVE, runtime_in_ms, solution, file)


def store_header(file: IO):
    header = "content_type,number_of_peers,opt_type,runtime_in_ms,success,objective,avg_delay\n"
    file.write(header.encode("utf-8"))

def store_record(content_type: ContentType,
                 number_of_peers: int,
                 opt_type: SingleTrackOptimizerType | MultiTrackOptimizerType,
                 runtime_in_ms: float,
                 solution: MultiTrackSolution,
                 file: IO):
    OPTIMIZER_ABBREVIATIONS = {
        SingleTrackOptimizerType.DIRECT_LINK_TREE: "DIR",
        SingleTrackOptimizerType.MULTICAST_HEURISTIC: "HEU",
        SingleTrackOptimizerType.INTEGER_LINEAR_PROGRAMMING: "ILP",
        SingleTrackOptimizerType.MINIMUM_SPANNING_TREE: "MST",
        MultiTrackOptimizerType.NATIVE: "NAT",
    }
    opt_name = OPTIMIZER_ABBREVIATIONS[opt_type]
    record = (content_type.name, str(number_of_peers), opt_name, f"{runtime_in_ms:.4f}", "1" if solution.success else "0", f"{solution.objective:.4f}", f"{solution.avg_delay:.4f}")
    record_line = ",".join(record) + "\n"
    file.write(record_line.encode("utf-8"))


def collect_optimization_info(network, tracks, multi_track_optimizer):
    start = time.time()
    solution = multi_track_optimizer(network, tracks)
    end = time.time()

    runtime_in_ms = (end - start) * 1000

    return (runtime_in_ms, solution)

if __name__ == "__main__":
    benchmark()
