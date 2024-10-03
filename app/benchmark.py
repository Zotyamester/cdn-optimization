import os
import sys
from enum import Enum
import time
from typing import IO
from sample import load_network
from solver import MultiTrackOptimizerType, MultiTrackSolution, SingleTrackOptimizerType, get_multi_track_optimizer, get_single_track_optimizer
from traffic import choose_peers, generate_broadcast_traffic
import signal


MAXIMUM_RUNTIME_IN_SECONDS = 8 * 3600


OPTIMIZER_ABBREVIATIONS = {
    SingleTrackOptimizerType.DIRECT_LINK_TREE: "DIR",
    SingleTrackOptimizerType.MULTICAST_HEURISTIC: "HEU",
    SingleTrackOptimizerType.INTEGER_LINEAR_PROGRAMMING: "ILP",
    SingleTrackOptimizerType.MINIMUM_SPANNING_TREE: "MST"
}


class ContentType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    MESSAGING = "text"
    GAMING = "gaming"


def generate_content(track_id, publisher, subscribers, content_type):
    LATENCIES = {
        ContentType.VIDEO: 400,
        ContentType.AUDIO: 150,
        ContentType.MESSAGING: 1000,
        ContentType.GAMING: 50,
    }

    tracks = generate_broadcast_traffic(
        track_id, publisher, subscribers, LATENCIES[content_type])
    return tracks


def benchmark(network, peers, min_peers, max_peers, step):
    timeout_in_seconds = MAXIMUM_RUNTIME_IN_SECONDS // max(1, len(ContentType) * (max_peers - min_peers + 1) // step)
    
    pid = os.getpid()
    with open(f"benchmark-{pid}-{time.strftime('%Y%m%d%H%M%S')}.csv", "wb", buffering=0) as file:
        store_header(file)

        for content_type in ContentType:
            track_id = f"{content_type.name}"
            
            # If for some value of number_of_peers, the optimization
            # times out, we skip it for the rest of the run (since it
            # is likely to timeout again when optimizing for more peers)
            to_be_skipped = set()

            for number_of_peers in range(min_peers, max_peers + 1, step):
                publisher, *subscribers = peers[:number_of_peers]
                tracks = generate_content(track_id, publisher, subscribers, content_type)

                for single_track_optimizer_type in SingleTrackOptimizerType:
                    if single_track_optimizer_type in to_be_skipped:
                        continue

                    single_track_optimizer = get_single_track_optimizer(
                        single_track_optimizer_type)
                    multi_track_optimizer = get_multi_track_optimizer(
                        MultiTrackOptimizerType.ADAPTED, single_track_optimizer=single_track_optimizer)

                    print(f"Running benchmarks for {content_type.name} with {number_of_peers} peers using {single_track_optimizer_type.name}")

                    def handler(_signum, _frame):
                        raise TimeoutError("Optimization timeout")

                    signal.signal(signal.SIGALRM, handler)
                    signal.alarm(timeout_in_seconds)

                    try:
                        runtime_in_ms, solution = collect_optimization_info(network, tracks, multi_track_optimizer)
                        store_record(content_type, number_of_peers, single_track_optimizer_type, runtime_in_ms, solution, file)
                        print(f"\tOptimization completed")
                    except TimeoutError:
                        to_be_skipped.add(single_track_optimizer_type)
                        store_dnf_record(content_type, number_of_peers, single_track_optimizer_type, file)
                        print(f"\tOptimization timed out")
                    except Exception as e:
                        print(f"\tAnother error has occured: {e}")

                    signal.alarm(0)


def store_header(file: IO):
    header = "content_type,number_of_peers,opt_type,runtime_in_ms,success,objective,avg_delay\n"
    file.write(header.encode("utf-8"))


def store_dnf_record(content_type: ContentType,
                     number_of_peers: int,
                     opt_type: SingleTrackOptimizerType | MultiTrackOptimizerType,
                     file: IO):
    opt_name = OPTIMIZER_ABBREVIATIONS[opt_type]
    record = (content_type.name, str(number_of_peers), opt_name, "DNF", "0", "-", "-")
    record_line = ",".join(record) + "\n"
    file.write(record_line.encode("utf-8"))


def store_record(content_type: ContentType,
                 number_of_peers: int,
                 opt_type: SingleTrackOptimizerType | MultiTrackOptimizerType,
                 runtime_in_ms: float,
                 solution: MultiTrackSolution,
                 file: IO):
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
    network = load_network("./datasource/azure_geant_topo.yaml")
    peers = choose_peers(network, network.number_of_nodes())

    n = os.cpu_count()

    pids = []
    
    for i in range(n):
        if (pid := os.fork()) == 0:
            benchmark(network, peers, 2 + i, min(2 + n + i, len(peers)), n)
            sys.exit(0)
        elif pid > 0:
            pids.append(pid)
        else:
            print(f"Error forking at {i}")
    
    for pid in pids:
        os.waitpid(pid, 0)
