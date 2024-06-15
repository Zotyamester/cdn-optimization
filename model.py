import geopy.distance
import itertools
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Node:
    location: tuple[float, float]  # (latitude, longitude)
    cost_factor: float

    def __iter__(self):
        yield from (self.location, self.cost_factor)


@dataclass
class Link:
    latency: float
    cost: float

    def __iter__(self):
        yield from (self.latency, self.cost)


class Network:
    LINK_PROPAGATION_SPEED = 200_000  # in km/s

    def __init__(self, nodes: dict[str, Node]):
        self.nodes = nodes
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

            cost_factor1 = self.nodes[node1].cost_factor
            cost_factor2 = self.nodes[node2].cost_factor

            link_usage_cost = (cost_factor1 + cost_factor2) / 2

            # Links are unidirectional, but there is a link in both ways with the same latency and usage cost
            self.links[(node1, node2)] = self.links[(node2, node1)
                                                    ] = Link(latency_in_ms, link_usage_cost)

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
    def __init__(self, name: str, publisher: str, subscribers: list[tuple[str, float]]):
        self.name = name
        self._publisher = publisher
        self._subscribers = subscribers
        self.recreate_streams()

    def recreate_streams(self):
        self.streams = {}
        for i, (subscriber, delay_budget) in enumerate(self._subscribers, start=1):
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
                ', '.join(map(lambda node_and_delay: node_and_delay[0], self._subscribers))}"

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


if __name__ == "__main__":
    nodes = {
        "eu-west-1":    Node((53.3498, -6.2603), 1.08),     # Dublin, IE
        "eu-west-2":    Node((51.5074, -0.1278), 1.26),     # London, GB
        "eu-west-3":    Node((48.8566, 2.3522), 1.08),      # Paris, FR
        "eu-central-1": Node((50.1109, 8.6821), 1.08),      # Frankfurt, DE
        "eu-north-1":   Node((59.3293, 18.0686), 0.094),    # Stockholm, SE
        "eu-south-1":   Node((45.4642, 9.1900), 1.08),      # Milan, IT
        "Aalborg":      Node((57.0169, 9.9891), 0.15),      # Aalborg, DK
        "Budapest":     Node((47.4732, 19.0379), 0.0029),   # Budapest, HU
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
