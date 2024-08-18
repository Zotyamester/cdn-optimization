from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from gcp_sample import network as model

class Network(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    nodes: list["Node"] = Relationship(back_populates="network")
    
    def get_nodes(self):
        return self.nodes
    def get_edges(self):
        return self.nodes.outgoing_edges + self.nodes.ingoing_edges


class Subscription(SQLModel, table=True):
    node_id: int = Field(foreign_key="node.id", primary_key=True, ondelete="CASCADE")
    track_id: int = Field(foreign_key="track.id", primary_key=True, ondelete="CASCADE")


class Node(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    network_id: int = Field(foreign_key="network.id", ondelete="CASCADE")
    name: str = Field(index=True)
    latitude: float
    longitude: float

    network: Network = Relationship(back_populates="nodes")

    out_edges: list["Edge"] = Relationship(back_populates="src_node", sa_relationship_kwargs=dict(primaryjoin="Edge.src_node_id==Node.id"))
    in_edges: list["Edge"] = Relationship(back_populates="dst_node", sa_relationship_kwargs=dict(primaryjoin="Edge.dst_node_id==Node.id"))

    tracks: list["Track"] = Relationship(back_populates="subscribers", link_model=Subscription)


class Edge(SQLModel, table=True):
    src_node_id: int = Field(foreign_key="node.id", primary_key=True, ondelete="CASCADE")
    dst_node_id: int = Field(foreign_key="node.id", primary_key=True, ondelete="CASCADE")
    delay: float = Field(ge=0.0)
    cost: float = Field(ge=0.0)

    src_node: Node = Relationship(back_populates="outgoing_edges", sa_relationship_kwargs=dict(foreign_keys="[Edge.src_node_id]"))
    dst_node: Node = Relationship(back_populates="ingoing_edges", sa_relationship_kwargs=dict(foreign_keys="[Edge.dst_node_id]"))


class Track(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    publisher: int = Field(foreign_key="node.id", ondelete="CASCADE")
    delay_bound: float = Field(ge=0.0)

    subscribers: list["Node"] = Relationship(back_populates="tracks", link_model=Subscription)


sqlite_url = "sqlite://"
engine = create_engine(sqlite_url, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def create_data_from_network():
    with Session(engine) as session:
        network = Network(
            name="test-network",
            nodes=[
                Node(
                    name=node,
                    latitude=attrs["location"][0], longitude=attrs["location"][1]
                )
                for node, attrs in model.nodes(data=True)
            ]
        )
        session.add(network)
        session.commit()
        # TODO: Add edges and tracks.


def dump_network():
    with Session(engine) as session:
        statement = select(Network)
        networks = session.exec(statement).all()
        for network in networks:
            print(f"Network: {network.name} ({network.id})")
            for node in network.nodes:
                print(f"\tNode: {node.name} ({node.id})")
                for edge in node.out_edges:
                    print(f"\t\tOut Edge: {edge.src_node.name} <-> {edge.dst_node.name}")
                for edge in node.in_edges:
                    print(f"\t\tIn Edge: {edge.src_node.name} <-> {edge.dst_node.name}")


def main():
    create_db_and_tables()
    create_data_from_network()
    dump_network()


if __name__ == "__main__":
    main()
