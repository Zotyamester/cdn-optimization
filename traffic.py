from model import Track


def generate_full_mesh_traffic(traffic_name: str, peers: list[str], latency: float):
    tracks = {}
    for i, peer in enumerate(peers, start=1):
        other_peers = list(filter(lambda x, peer=peer: x != peer, peers))
        tracks[f"t{i}"] = Track(
            name=f"{traffic_name}-of-{peer}",
            publisher=peer,
            subscribers=dict(zip(other_peers, [latency] * len(other_peers))),
        )
    return tracks


def generate_video_conference_traffic(peers: list[str], latency: float = 1200):
    return generate_full_mesh_traffic("video", peers, latency)


def generate_live_video_traffic(publishers: list[tuple[str, list[str]]], qci_table: list[int], subscribers: list[tuple[str, int, set[str]]]) -> dict[str, Track]:
    tracks = {}

    i = 1
    for publisher, contents in publishers:
        for content in contents:
            tracks[f"t{i}"] = Track(
                name=content,
                publisher=publisher,
                subscribers={
                    subscriber: qci_table[qci] for subscriber, qci, desired_contents in subscribers if content in desired_contents
                },
            )
            i += 1

    return tracks
