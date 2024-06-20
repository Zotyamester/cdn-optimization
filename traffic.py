from model import Track


def generate_full_mesh_traffic(traffic_name: str, peers: list[str], latency: float):
    tracks = {}
    for i, peer in enumerate(peers, start=1):
        other_peers = list(filter(lambda x, peer=peer: x != peer, peers))
        tracks[f"t{i}"] = Track(
            name=f"{traffic_name}-of-{peer}",
            publisher=peer,
            subscribers=list(
                zip(other_peers, [latency] * len(other_peers))
            )
        )
    return tracks


def generate_video_conference_traffic(peers: list[str]):
    VIDEO_CONFERENCE_LATENCY = 250  # ms
    return generate_full_mesh_traffic("video", peers, VIDEO_CONFERENCE_LATENCY)


def generate_live_video_traffic():
    tracks = {
        "t1": Track(
            name="Gajdos Összes Rövidítve",
            publisher="eu-central-1",
            subscribers=[
                ("Budapest", 95),
                ("Aalborg", 5),
                ("eu-north-1", 16),
                ("eu-south-1", 10),
                ("us-east-1", 40),
                ("us-west-1", 70),
                ("us-west-2", 80),
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
    return tracks
