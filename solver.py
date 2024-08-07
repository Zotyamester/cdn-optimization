from collections import namedtuple
import math
from typing import Callable

import networkx as nx
import pulp as lp

from model import Track


class SingleTrackSolution:
    def __init__(self, success: bool, objective: float, used_links: list[tuple[str, str]]):
        self.success = success
        self.objective = objective
        self.used_links = used_links

    def __iter__(self):
        yield from (self.success, self.objective, self.used_links)

    @staticmethod
    def found(objective: float, used_links: list[tuple[str, str]]) -> 'SingleTrackSolution':
        return SingleTrackSolution(True, objective, used_links)

    @staticmethod
    def not_found() -> 'SingleTrackSolution':
        return SingleTrackSolution(False, 0.0, [])


# Spectrum::LeftMost - Keeping the delay constraints
def direct_link_tree(graph: nx.Graph, track: Track) -> SingleTrackSolution:
    cost = 0.0
    edges = []
    for subscriber in track.subscribers:
        edge = (track.publisher, subscriber)

        data = graph.get_edge_data(*edge)
        if data["latency"] > track.delay_budget:
            return SingleTrackSolution.not_found()

        cost += data["cost"]
        edges.append(edge)

    return SingleTrackSolution.found(cost, edges)


# Spectrum::Left - Approximately optimal in cost while keeping the delay constraints
def multicast_heuristic(graph: nx.DiGraph, track: Track) -> SingleTrackSolution:
    latencies = {track.publisher: 0.0}
    cost = 0.0
    tree = nx.DiGraph()
    tree.add_node(track.publisher)

    for node in track.subscribers:
        if node == track.publisher:
            continue

        # Find the best edge to connect the node to the tree (without reordering the whole tree)

        best_edge = min(
            filter(
                lambda edge, node=node:
                    edge[0] in tree.nodes and
                    edge[1] == node and
                    latencies[edge[0]] +
                    graph.get_edge_data(
                        *edge
                    )["latency"] <= track.delay_budget,
                graph.edges
            ),
            key=lambda edge: (graph.get_edge_data(
                *edge)["cost"], graph.get_edge_data(*edge)["latency"]),
            default=None
        )

        # Didn't find any suitable edge (i.e., not even the direct link to the publisher would work)
        if best_edge is None:
            return SingleTrackSolution.not_found()

        connection_node = best_edge[0]

        # See if we can improve one of our existing connections by redirecting traffic through the new node

        Replacement = namedtuple("Replacement", [
                                 "new_edge", "old_edge", "subtree", "delay_balance", "cost_balance"])
        best_replacement = Replacement(None, None, [], 0.0, math.inf)

        loop_causing_nodes = {node} | set(nx.shortest_path(tree, track.publisher, connection_node))

        for tree_node in set(tree.nodes) - loop_causing_nodes:
            previous_node = nx.shortest_path(tree, track.publisher, tree_node)[-2]

            to_be_replaced_edge = (previous_node, tree_node)
            replacement_edge = (node, tree_node)

            delay_balance = graph.get_edge_data(
                *replacement_edge)["latency"] - graph.get_edge_data(*to_be_replaced_edge)["latency"]
            cost_balance = graph.get_edge_data(
                *replacement_edge)["cost"] - graph.get_edge_data(*to_be_replaced_edge)["cost"]

            # If the delay budget could not be met by redirecting the traffic, continue
            subtree = [v for _, v in nx.bfs_edges(tree, tree_node)]
            if not all(latencies[v] + delay_balance for v in subtree):
                continue

            # Note that if the balance negative, it's a cost reduction
            if cost_balance < best_replacement.cost_balance:
                best_replacement = Replacement(
                    replacement_edge, to_be_replaced_edge, subtree, delay_balance, cost_balance)

        if best_replacement.cost_balance < 0 or (best_replacement.cost_balance == 0 and best_replacement.delay_balance < 0):
            tree.remove_edge(*best_replacement.old_edge)
            tree.add_edge(*best_replacement.new_edge)
            cost += best_replacement.cost_balance
            for v in best_replacement.subtree:
                latencies[v] += best_replacement.delay_balance

        # Add the edge to the tree and update the cost and latencies

        edge_data = graph.get_edge_data(*best_edge)
        best_cost, best_latency = edge_data["cost"], edge_data["latency"]

        tree.add_edge(*best_edge)
        cost += best_cost
        latencies[node] = latencies[connection_node] + best_latency

    return SingleTrackSolution.found(cost, list(tree.edges))


# Spectrum::Right - Optimal in cost while keeping the delay constraints
def get_optimal_topology_for_a_single_track(network: nx.DiGraph, track: Track) -> SingleTrackSolution:
    prob = lp.LpProblem("MoQ_relay_topology_optimization", lp.LpMinimize)

    # xfij == x_{stream}_{link}; xfij >= 0 constraint is always satisfied
    transmission_bitrates = lp.LpVariable.dicts(
        "x", (track.streams.keys(), network.edges), 0, None, cat=lp.LpContinuous)

    # yij == y_{link}; yij >= 0 constraint is always satisfied
    link_usages = lp.LpVariable.dicts(
        "y", network.edges, 0, None, cat=lp.LpContinuous)

    # zfij == z_{stream}_{link}; zij == 0 or 1
    selected_links = lp.LpVariable.dicts(
        "z", (track.streams.keys(), network.edges), 0, 1, cat=lp.LpBinary)

    # Objective function
    prob += lp.lpSum([data["cost"] * link_usages[(node1, node2)] for node1, node2, data
                      in network.edges(data=True)]), "total_link_usage"

    # Constraint: yij >= xfij
    for stream in track.streams.keys():
        for link in network.edges:
            prob += link_usages[link] >= transmission_bitrates[stream][link], \
                f"y_({link[0]},{link[1]})>=x_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(xfji) - sum(xfij) == Rfi
    for stream, node_reliabilities in track.streams.items():
        for node in network.nodes.keys():
            # Devlog: This constraint causes problems when using undirected graphs.
            #         The network should obviously be directed, since otherwise "in-going" and "out-going"
            #         traffic will be indistinguishable, and as such, the equation might not hold.
            in_going = lp.lpSum([transmission_bitrates[stream][link]
                                for link in network.edges if link[1] == node])
            out_going = lp.lpSum([transmission_bitrates[stream][link]
                                  for link in network.edges if link[0] == node])
            prob += in_going - out_going == node_reliabilities[node], \
                f"nodal_balance_for_{stream}_{node}"

    # Constraint: zfij*M >= xfij
    M = 1e4  # Some large number
    for stream in track.streams.keys():
        for link in network.edges:
            prob += selected_links[stream][link] * M >= transmission_bitrates[stream][link], \
                f"z_{stream}_({link[0]},{
                link[1]})*M>=x_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(zfij * dij) <= Df
    for stream in track.streams.keys():
        prob += lp.lpSum([selected_links[stream][(node1, node2)] * data["latency"]
                          for node1, node2, data in network.edges(data=True)]) <= track.delay_budget, \
            f"delay_budget_for_{stream}"

    prob.solve(lp.PULP_CBC_CMD(msg=False))

    success = prob.status == lp.LpStatusOptimal
    if not success:
        return SingleTrackSolution.not_found()

    objective = prob.objective.value()
    used_links = [link for link, var in link_usages.items()
                  if var.varValue > 0]
    return SingleTrackSolution.found(objective, used_links)


# Spectrum::RightMost - Optimal in cost
def minimum_spanning_tree(graph: nx.DiGraph, track: Track) -> SingleTrackSolution:
    graph = graph.to_undirected()
    graph.remove_nodes_from(
        set(graph.nodes) - {track.publisher} - set(track.subscribers))

    mst = nx.minimum_spanning_tree(graph, weight="cost")
    mst_from_publisher = nx.bfs_tree(mst, track.publisher)

    cost = 0.0
    latencies = {track.publisher: 0.0}
    for u, v in mst_from_publisher.edges:
        data = graph.get_edge_data(u, v)

        cost += data["cost"]
        latencies[v] = latencies[u] + data["latency"]

        if latencies[v] > track.delay_budget:
            return SingleTrackSolution.not_found()

    return SingleTrackSolution.found(cost, list(mst_from_publisher.edges))


class MultiTrackSolution:
    def __init__(self, success: bool, objective: float, used_links_per_track: dict[str, list[tuple[str, str]]]):
        self.success = success
        self.objective = objective
        self.used_links_per_track = used_links_per_track

    def __iter__(self):
        yield from (self.success, self.objective, self.used_links_per_track)

    @staticmethod
    def found(objective: float, used_links_per_track: dict[str, list[tuple[str, str]]]) -> 'MultiTrackSolution':
        return MultiTrackSolution(True, objective, used_links_per_track)

    @staticmethod
    def not_found() -> 'MultiTrackSolution':
        return MultiTrackSolution(False, 0.0, {})


def multi_to_single_track_adapter_factory(strategy: Callable[[nx.DiGraph, Track], SingleTrackSolution]) -> Callable[[nx.DiGraph, Track], MultiTrackSolution]:

    def multi_to_single_track_adapter(network: nx.DiGraph, tracks: dict[str, Track]) -> MultiTrackSolution:
        objective = 0.0
        used_links_per_track = {}

        for track_id, track in tracks.items():
            track_success, track_objective, used_links = strategy(
                network, track)
            if not track_success:
                return MultiTrackSolution.not_found()

            objective += track_objective
            used_links_per_track[track_id] = used_links

        return MultiTrackSolution.found(objective, used_links_per_track)

    return multi_to_single_track_adapter


def get_optimal_topology_for_multiple_tracks(network: nx.DiGraph, tracks: dict[str, Track]) -> MultiTrackSolution:
    prob = lp.LpProblem("MoQ_relay_topology_optimization", lp.LpMinimize)

    # xftij == x_{track}_{stream}_{link}; xftij >= 0 constraint is always satisfied
    transmission_bitrates = {}
    for track_id, track in tracks.items():
        transmission_bitrates[track_id] = lp.LpVariable.dicts(
            f"x_{track_id}", (track.streams.keys(), network.edges), 0, None, cat=lp.LpContinuous)

    # ytij == y_{track}_{link}; ytij >= 0 constraint is always satisfied
    link_usages = lp.LpVariable.dicts(
        "y", (tracks.keys(), network.edges), 0, None, cat=lp.LpContinuous)

    # zftij == z_{track}_{stream}_{link}; ztij == 0 or 1
    selected_links = {}
    for track_id, track in tracks.items():
        selected_links[track_id] = lp.LpVariable.dicts(
            f"z_{track_id}", (track.streams.keys(), network.edges), 0, 1, cat=lp.LpBinary)

    # Objective function
    prob += lp.lpSum([data["cost"] * link_usages[track_id][(node1, node2)] for node1, node2, data
                     in network.edges(data=True) for track_id in tracks.keys()]), "total_link_usage"

    # Constraint: ytij >= xftij
    for track_id, track in tracks.items():
        for stream in track.streams.keys():
            for link in network.edges:
                prob += link_usages[track_id][link] >= transmission_bitrates[track_id][stream][link], \
                    f"y_{track_id}_({link[0]},{link[1]})>=x_{track_id}_{
                    stream}_({link[0]},{link[1]})"

    # Constraint: sum(xftji) - sum(xftij) == Rfti
    for track_id, track in tracks.items():
        for stream, node_reliabilities in track.streams.items():
            for node in network.nodes.keys():
                # Devlog: This constraint causes problems when using undirected graphs.
                #         The network should obviously be directed, since otherwise "in-going" and "out-going"
                #         traffic will be indistinguishable, and as such, the equation might not hold.
                in_going = lp.lpSum([transmission_bitrates[track_id][stream][link]
                                    for link in network.edges if link[1] == node])
                out_going = lp.lpSum([transmission_bitrates[track_id][stream][link]
                                      for link in network.edges if link[0] == node])
                prob += in_going - out_going == node_reliabilities[node], \
                    f"nodal_balance_for_{track_id}_{stream}_{node}"

    # Constraint: zftij*M >= xftij
    M = 1e4  # Some large number
    for track_id, track in tracks.items():
        for stream in track.streams.keys():
            for link in network.edges:
                prob += selected_links[track_id][stream][link] * M >= transmission_bitrates[track_id][stream][link], \
                    f"z_{track_id}_{stream}_({link[0]},{
                    link[1]})*M>=x_{track_id}_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(zftij * dij) <= Dft
    for track_id, track in tracks.items():
        for stream, (delay_budget, _) in track.streams.items():
            prob += lp.lpSum([selected_links[track_id][stream][(node1, node2)] * data["latency"]
                              for node1, node2, data in network.edges(data=True)]) <= delay_budget, \
                f"delay_budget_for_{track_id}_{stream}"

    prob.solve(lp.PULP_CBC_CMD(msg=False))

    success = prob.status == lp.LpStatusOptimal
    if not success:
        return MultiTrackSolution.not_found()

    objective = prob.objective.value()
    used_links_per_track = {}
    for track_id in tracks.keys():
        used_links_per_track[track_id] = [
            link for link, var in link_usages[track_id].items() if var.varValue > 0]
    return MultiTrackSolution.found(objective, used_links_per_track)


def get_multi_track_optimizer(type: str) -> Callable[[nx.DiGraph, dict[str, Track], bool], MultiTrackSolution]:
    if type == "single":
        return multi_to_single_track_adapter_factory(get_optimal_topology_for_a_single_track)
    elif type == "multiple":
        return get_optimal_topology_for_multiple_tracks
    else:
        raise ValueError("Invalid optimizer type.")
