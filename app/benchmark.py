
from enum import Enum
import random
import time
from sample import store_network
from model import load_geant_json
from overlay_underlay import create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping, load_base_network
from solver import MultiTrackOptimizerType, SingleTrackOptimizerType, get_multi_track_optimizer, get_single_track_optimizer
from traffic import choose_peers, generate_broadcast_traffic, generate_continental_relays


def benchmark():
    store = []

    cdn_nodes = generate_continental_relays(7, 10)

    base_network = load_base_network(load_geant_json("./datasource/geant.json"), "GEANT")
    underlay_network = create_underlay_network(base_network, cdn_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, cdn_nodes)
    overlay_network = create_overlay_network(underlay_network, cdn_nodes, mapping)
    network = overlay_network
    store_network(network, "./datasource/random_benchmark.yaml")

    for content_type in ContentType:
        track_id = f"{content_type.name}"

        for number_of_peers in range(2, 4):#len(cdn_nodes) + 1):
            publisher, *subscribers = choose_peers(network, number_of_peers)
            tracks = generate_content(track_id, publisher, subscribers, content_type)

            for single_track_optimizer_type in SingleTrackOptimizerType:
                single_track_optimizer = get_single_track_optimizer(single_track_optimizer_type)
                multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizerType.ADAPTED, single_track_optimizer=single_track_optimizer)

                store.append((content_type, number_of_peers, single_track_optimizer_type, collect_optimization_info(network, tracks, multi_track_optimizer)))
            
            multi_track_optimizer = get_multi_track_optimizer(MultiTrackOptimizerType.NATIVE)
            store.append((content_type, number_of_peers, MultiTrackOptimizerType.NATIVE, collect_optimization_info(network, tracks, multi_track_optimizer)))

    with open("benchmark.csv", "w") as file:
        for content_type, number_of_peers, optimizer_type, optimization_info in store:
            runtime_in_ms, solution = optimization_info
            file.write(f"{content_type.name},{number_of_peers},{optimizer_type.name},{runtime_in_ms},{solution.success},{solution.objective}\n")

def collect_optimization_info(network, tracks, multi_track_optimizer):
    start = time.time()
    solution = multi_track_optimizer(network, tracks)
    end = time.time()
    runtime_in_ms = (end - start) * 1000
    return (runtime_in_ms, solution)

class ContentType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    GAMING = "image"
    MESSAGING = "text"

def generate_content(track_id, publisher, subscribers, content_type):
    LATENCIES = {
        ContentType.VIDEO: 500,
        ContentType.AUDIO: 200,
        ContentType.GAMING: 50,
        ContentType.MESSAGING: 1000
    }

    tracks = generate_broadcast_traffic(track_id, publisher, subscribers, LATENCIES[content_type])
    return tracks

if __name__ == "__main__":
    benchmark()