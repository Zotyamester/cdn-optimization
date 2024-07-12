from typing import Callable
import geopy.distance
import itertools
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Node:
    location: tuple[float, float]  # (latitude, longitude)

    def __iter__(self):
        yield from (self.location,)


@dataclass
class Link:
    latency: float
    cost: float

    def __iter__(self):
        yield from (self.latency, self.cost)


class Network:
    LINK_PROPAGATION_SPEED = 200_000  # in km/s

    def __init__(self,
                 nodes: dict[str, Node],
                 calculate_cost: Callable[[dict[str, Node], str, str], float]):
        self.nodes = nodes
        self.calculate_cost = calculate_cost
        self.recreate_links()

    def recreate_links(self):
        self.links = {}

        # Calculate distance between every pair of cities and add a link in both directions
        for node1, node2 in itertools.combinations(self.nodes.keys(), 2):
            coords1 = self.nodes[node1].location
            coords2 = self.nodes[node2].location

            distance = geopy.distance.geodesic(coords1, coords2).km
            latency_in_s = distance / Network.LINK_PROPAGATION_SPEED
            latency_in_ms = latency_in_s * 1000

            link_usage_cost = self.calculate_cost(self.nodes, node1, node2)

            # Links are unidirectional, but there is a link in both ways with the same latency and usage cost
            link = Link(latency_in_ms, link_usage_cost)
            self.links[(node1, node2)] = self.links[(node2, node1)] = link

    def __iter__(self):
        yield from (self.nodes.items(), self.links.items())

    def __str__(self) -> str:
        return f"Network of {', '.join(self.nodes.keys())}"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class Stream:
    delay_budget: int
    node_reliabilities: dict

    def __iter__(self):
        yield from (self.delay_budget, self.node_reliabilities)


class Track:
    def __init__(self, name: str, publisher: str, subscribers: dict[str, float]):
        self.name = name
        self._publisher = publisher
        self._subscribers = subscribers
        self.recreate_streams()

    def recreate_streams(self):
        self.streams = {}
        for i, (subscriber, delay_budget) in enumerate(self._subscribers.items(), start=1):
            stream_id = f"f{i}"
            self.streams[stream_id] = Stream(
                delay_budget,
                defaultdict(lambda: 0, {
                    self._publisher: -1,
                    subscriber: 1
                })
            )

    def __iter__(self):
        yield from (self.name, self.streams.items())

    def __str__(self) -> str:
        return f"Track {self.name}: " \
            f"{self._publisher} -> {
                ', '.join(map(lambda node_and_delay: node_and_delay[0], self._subscribers.items()))}"

    def __repr__(self) -> str:
        return str(self)


def display_network_links(network: Network):
    print("Links:")
    for link, (latency, cost) in sorted(network.links.items(), key=lambda kv: kv[1].latency):
        print(f" * {' <-> '.join(link)}:\t\t{latency:.2f} ms\t\t{cost:.2f}")
    print()


def display_track_stats(nodes: dict[str, Node], tracks: dict[str, Track]):
    print("Tracks:")
    for track_id, (name, streams) in tracks.items():
        print(f"\t{track_id} ({name}):")

        for stream_id, (delay_budget, node_reliabilities) in streams:
            print(f"\t\t{stream_id}: {delay_budget} ms")

            for node in nodes.keys():
                print(f"\t\t\t{node}: {node_reliabilities[node]}", end="")

                if node_reliabilities[node] < 0:
                    print(" (pub)")
                elif node_reliabilities[node] > 0:
                    print(" (sub)")
                else:
                    print("")
        print()
