import sys
from model import create_graph, display_triangle_inequality_satisfaction
import networkx as nx
import yaml


def calculate_cost_factory(link_costs: dict[tuple[str, str], float]):
    def calculate_cost(_, node1, node2):
        link = (node1, node2)
        if link in link_costs:
            return link_costs[link]
        reverse_link = (node2, node1)
        if reverse_link in link_costs:
            return link_costs[reverse_link]
        raise ValueError(f"Link cost not found for {link} or {reverse_link}")

    return calculate_cost


def load_network(file_path: str) -> nx.DiGraph:
    with open(file_path, "r") as file:
        topo_data = yaml.safe_load(file)

    nodes = [
        (node["name"], {"location": tuple(node["location"])})
        for node in topo_data["nodes"]
    ]

    link_costs = {}

    for edge in topo_data["edges"]:
        node1 = edge["node1"]
        node2 = edge["node2"]
        cost = edge["attributes"]["cost"]
        link_costs[(node1, node2)] = cost

    return create_graph(nodes, calculate_cost=calculate_cost_factory(link_costs))


def store_network(network: nx.DiGraph, file_path: str):
    nodes = [
        {"name": node, "location": list(attrs["location"])}
        for node, attrs in network.nodes(data=True)
    ]

    edges = [
        {"node1": node1, "node2": node2, "attributes": dict(attrs)}
        for node1, node2, attrs in network.edges(data=True)
    ]

    with open(file_path, "w") as file:
        yaml.dump({"nodes": nodes, "edges": edges}, file)


if __name__ == "__main__":
    display_triangle_inequality_satisfaction(load_network(
        sys.argv[1] if len(sys.argv) > 1 else "datasource/small_topo.yaml"))
