from functools import reduce
import os
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select, delete


model = ...


class Network(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    node_list: list["Node"] = Relationship(back_populates="network")

    def nodes(self):
        return self.node_list

    def edges(self):
        # Could also use node.out_edges; but it doesn't matter, since an in-edge of a node is always an out-edge of another.
        return list(reduce(lambda edges1, edges2: edges1 + edges2, map(lambda node: node.in_edges, self.node_list), []))


class Subscription(SQLModel, table=True):
    node_id: int = Field(foreign_key="node.id",
                         primary_key=True, ondelete="CASCADE")
    track_id: int = Field(foreign_key="track.id",
                          primary_key=True, ondelete="CASCADE")


class LinkUsage(SQLModel, table=True):
    track_id: int = Field(primary_key=True, foreign_key="track.id", ondelete="CASCADE")
    edge_id: int = Field(primary_key=True, foreign_key="edge.id", ondelete="CASCADE")


class Node(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    network_id: int = Field(foreign_key="network.id", ondelete="CASCADE")

    name: str = Field(index=True)
    lat: float
    lon: float

    network: Network = Relationship(back_populates="node_list")

    out_edges: list["Edge"] = Relationship(
        back_populates="src_node", sa_relationship_kwargs=dict(primaryjoin="Edge.src_node_id==Node.id"))
    in_edges: list["Edge"] = Relationship(back_populates="dst_node", sa_relationship_kwargs=dict(
        primaryjoin="Edge.dst_node_id==Node.id"))

    tracks: list["Track"] = Relationship(
        back_populates="subscribers", link_model=Subscription)
    published_tracks: list["Track"] = Relationship(back_populates="publisher")


class Edge(SQLModel, table=True):
    src_node_id: int = Field(foreign_key="node.id",
                             primary_key=True, ondelete="CASCADE")
    dst_node_id: int = Field(foreign_key="node.id",
                             primary_key=True, ondelete="CASCADE")
    latency: float = Field(ge=0.0)
    cost: float = Field(ge=0.0)

    src_node: Node = Relationship(back_populates="out_edges", sa_relationship_kwargs=dict(
        foreign_keys="[Edge.src_node_id]"))
    dst_node: Node = Relationship(back_populates="in_edges", sa_relationship_kwargs=dict(
        foreign_keys="[Edge.dst_node_id]"))

    active_tracks: list["Track"] = Relationship(
        back_populates="used_links", link_model=LinkUsage)

    def __iter__(self):
        yield from (self.src_node_id, self.dst_node_id, self.latency, self.cost)


class Track(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # Idiomatic name for the track.
    name: str = Field(unique=True, nullable=False, index=True, min_length=1)
    # Publisher node.
    publisher_id: int = Field(foreign_key="node.id", ondelete="CASCADE")
    # Delay bound for the track's content.
    delay_bound: float = Field(ge=0.0)

    publisher: Node = Relationship(back_populates="published_tracks")
    subscribers: list["Node"] = Relationship(
        back_populates="tracks", link_model=Subscription)

    used_links: list["Edge"] = Relationship(
        back_populates="active_tracks", link_model=LinkUsage)


DB_USER = os.environ.get("DB_USER", "postgres")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}"

engine = create_engine(DB_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def delete_db_data():
    with Session(engine) as session:
        session.exec(delete(Network))


def create_db_data_from_network():
    with Session(engine) as session:
        network = Network(
            name="test-network",
            node_list=[
                Node(
                    name=node,
                    lat=attrs["location"][0], lon=attrs["location"][1]
                )
                for node, attrs in model.nodes(data=True)
            ]
        )
        session.add(network)
        session.commit()

        name_resolution_table = {
            node.name: node.id for node in network.node_list}
        for src, dst, attrs in model.edges(data=True):
            src_id, dst_id = name_resolution_table[src], name_resolution_table[dst]
            edge = Edge(src_node_id=src_id, dst_node_id=dst_id,
                        latency=attrs["latency"], cost=attrs["cost"])
            session.add(edge)
        session.commit()


def dump_network():
    with Session(engine) as session:
        statement = select(Network)
        networks = session.exec(statement).all()
        for network in networks:
            print(f"Network: {network.name} ({network.id})")
            for node in network.node_list:
                print(f"\tNode: {node.name} ({node.id})")
                for edge in node.out_edges:
                    print(f"\t\tOut Edge: {
                          edge.src_node.name} <-> {edge.dst_node.name} ({edge.latency} ms, {edge.cost} USD)")
                for edge in node.in_edges:
                    print(f"\t\tIn Edge: {
                          edge.src_node.name} <-> {edge.dst_node.name} ({edge.latency} ms, {edge.cost} USD)")


def main():
    create_db_and_tables()
    delete_db_data()
    create_db_data_from_network()
    dump_network()


if __name__ == "__main__":
    main()
