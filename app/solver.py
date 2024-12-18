from collections import namedtuple
from enum import Enum
import math
from typing import Callable

import networkx as nx
import pulp as lp

from model import Track


class SingleTrackSolution:
    def __init__(self, success: bool, cost: float, max_delay: float, used_links: list[tuple[str, str]]):
        self.success = success
        self.cost = cost
        self.max_delay = max_delay
        self.used_links = used_links

    def __iter__(self):
        yield from (self.success, self.cost, self.max_delay, self.used_links)

    @staticmethod
    def found(cost: float, max_delay: float, used_links: list[tuple[str, str]]) -> 'SingleTrackSolution':
        return SingleTrackSolution(True, cost, max_delay, used_links)

    @staticmethod
    def not_found() -> 'SingleTrackSolution':
        return SingleTrackSolution(False, 0.0, 0.0, [])


# Spectrum::LeftMost - Keeping the delay constraints
def direct_link_tree(network: nx.Graph, track: Track) -> SingleTrackSolution:
    cost = 0.0
    max_delay = 0.0
    edges = []

    for subscriber in track.subscribers:
        edge = (track.publisher, subscriber)

        data = network.get_edge_data(*edge)

        max_delay = max(max_delay, data["latency"])
        if max_delay > track.delay_budget:
            return SingleTrackSolution.not_found()
        cost += data["cost"]
        edges.append(edge)


    return SingleTrackSolution.found(cost, max_delay, edges)


# Spectrum::Left - Approximately optimal in cost while keeping the delay constraints
def multicast_heuristic(network: nx.DiGraph, track: Track) -> SingleTrackSolution:
    # Suppose that n is the number of subscribers and m is the number of links in the tree

    latencies = {track.publisher: 0.0}
    cost = 0.0
    tree = nx.DiGraph()
    tree.add_node(track.publisher)

    # O(1) ideally (if a reverse edge list is stored in the graph representation), otherwise implementation-defined
    def previous_in_tree(node: str) -> str:
        return list(tree.in_edges(node))[0][0]

    # O(n) + O(n + m) ≈ O(n)
    # └┬─┘   └──┬───┘
    #  │        └─ BFS's base complexity (assuming edge lists are used),
    #  │           but since it's executed on a tree, m will be at most n - 1,
    #  │           thus it reduces to O(n + n) ≈ O(n)
    #  └─ list comprehension's complexity
    def subtree_in_tree(node: str) -> list[str]:
        return nx.bfs_tree(tree, node).nodes

    # O(n) * O(1) ≈ O(n)
    def reverse_path_to_root(node: str) -> list[str]:
        path = []
        while True:
            path.append(node)
            if node == track.publisher:
                break
            node = previous_in_tree(node)
        path.reverse()
        return path

    # O(n) + O(n) * (O(n) + O(n)) + O(n) ≈ O(n) + O(n²) + O(n) ≈ O(n²)
    def augment(node: str):
        nonlocal network, latencies, cost, tree

        Replacement = namedtuple("Replacement", [
            "new_edge", "old_edge", "subtree", "delay_balance", "cost_balance"])
        best_replacement = Replacement(None, None, [], 0.0, math.inf)

        # This assertion should hold true, since `tree` MUST be a tree graph in any given point in time,
        # thus a shortest path between two node is the one and only path between them.
        #   assert list(nx.shortest_path(tree, track.publisher, node)) == reverse_path_to_root(node)
        loop_causing_nodes = set(reverse_path_to_root(node))

        for tree_node in set(tree.nodes) - loop_causing_nodes:
            # This assertion should hold true, since `tree` MUST be a tree graph in any given point in time,
            # thus a shortest path between two node is the one and only path between them, and also in a
            # directed tree, there must be at most one parent for each node (more specifically: 0 for root,
            # and 1 for every other node):
            #   assert nx.shortest_path(tree, track.publisher, tree_node)[-2] == previous_in_tree(tree_node)
            previous_node = previous_in_tree(tree_node)

            to_be_replaced_edge = (previous_node, tree_node)
            replacement_edge = (node, tree_node)

            new_base_e2e_delay = latencies[node] + network.get_edge_data(*replacement_edge)["latency"]
            old_base_e2e_delay = latencies[previous_node] + network.get_edge_data(*to_be_replaced_edge)["latency"]
            delay_balance = new_base_e2e_delay - old_base_e2e_delay

            cost_balance = network.get_edge_data(*replacement_edge)["cost"] - network.get_edge_data(*to_be_replaced_edge)["cost"]

            subtree = subtree_in_tree(tree_node)

            # If the delay budget is met by redirecting the traffic, and the replacement comes with cost reductions
            if all(latencies[v] + delay_balance < track.delay_budget for v in subtree) and cost_balance < best_replacement.cost_balance:
                best_replacement = Replacement(replacement_edge, to_be_replaced_edge, subtree, delay_balance, cost_balance)

        if best_replacement.cost_balance < 0 or (best_replacement.cost_balance == 0 and best_replacement.delay_balance < 0):
            tree.remove_edge(*best_replacement.old_edge)
            tree.add_edge(*best_replacement.new_edge)
            cost += best_replacement.cost_balance
            for v in best_replacement.subtree:
                latencies[v] += best_replacement.delay_balance

    # O(n) + O(n²) ≈ O(n²)
    def add_subscriber(node: str) -> str | None:
        nonlocal network, track, latencies, cost, tree

        # Find the best edge to connect the node to the tree (without reordering the whole tree)
        best_edge = min(
            filter(
                lambda edge, node=node:
                    edge[0] in tree.nodes and
                    edge[1] == node and
                    latencies[edge[0]] + network.get_edge_data(*edge)["latency"] <= track.delay_budget,
                network.edges
            ),
            key=lambda edge: (
                network.get_edge_data(*edge)["cost"],
                latencies[edge[0]] + network.get_edge_data(*edge)["latency"]
            ),
            default=None
        )

        # Didn't find any suitable edge (i.e., not even the direct link to the publisher would work)
        if best_edge is None:
            return None

        # Add the edge to the tree
        connection_node = best_edge[0]
        tree.add_edge(*best_edge)

        # Update the cost and latency values
        best_data = network.get_edge_data(*best_edge)
        cost += best_data["cost"]
        latencies[node] = latencies[connection_node] + best_data["latency"]

        # See if we can improve one of our existing connections by redirecting traffic through the newly added node
        augment(node)

        return connection_node

    # O(n) * O(n²) ≈ O(n³)
    for node in track.subscribers:
        if add_subscriber(node) is None:
            return SingleTrackSolution.not_found()

    # O(n)
    max_delay = max(latencies.values())

    return SingleTrackSolution.found(cost, max_delay, list(tree.edges))


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
                f"z_{stream}_({link[0]},{link[1]})*M>=x_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(zfij * dij) <= D
    for stream in track.streams.keys():
        prob += lp.lpSum([selected_links[stream][(node1, node2)] * data["latency"]
                          for node1, node2, data in network.edges(data=True)]) <= track.delay_budget, \
            f"delay_budget_for_{stream}"

    prob.solve(lp.PULP_CBC_CMD(msg=False))

    success = prob.status == lp.LpStatusOptimal
    if not success:
        return SingleTrackSolution.not_found()

    cost = prob.objective.value()
    max_delay = max(track.delay_budget + prob.constraints[f"delay_budget_for_{stream}"].value() for stream in track.streams.keys())
    used_links = [link for link, var in link_usages.items()
                  if var.varValue > 0]
    return SingleTrackSolution.found(cost, max_delay, used_links)


# Spectrum::RightMost - Optimal in cost
def minimum_spanning_tree(network: nx.DiGraph, track: Track) -> SingleTrackSolution:
    network = network.to_undirected()
    network.remove_nodes_from(
        set(network.nodes) - {track.publisher, *track.subscribers})

    mst = nx.minimum_spanning_tree(network, weight="cost")
    mst_from_publisher = nx.bfs_tree(mst, track.publisher)

    cost = 0.0
    max_delay = 0.0
    latencies = {track.publisher: 0.0}
    for u, v in mst_from_publisher.edges:
        data = network.get_edge_data(u, v)

        cost += data["cost"]
        latencies[v] = latencies[u] + data["latency"]

        max_delay = max(max_delay, latencies[v])
        if max_delay > track.delay_budget:
            return SingleTrackSolution.not_found()

    return SingleTrackSolution.found(cost, max_delay, list(mst_from_publisher.edges))


class SingleTrackOptimizerType(str, Enum):
    DIRECT_LINK_TREE = "direct_link_tree"
    MULTICAST_HEURISTIC = "multicast_heuristic"
    INTEGER_LINEAR_PROGRAMMING = "integer_linear_programming"
    MINIMUM_SPANNING_TREE = "minimum_spanning_tree"


def get_single_track_optimizer(type: SingleTrackOptimizerType) -> Callable[[nx.DiGraph, Track], SingleTrackSolution]:
    if type == SingleTrackOptimizerType.DIRECT_LINK_TREE:
        return direct_link_tree
    elif type == SingleTrackOptimizerType.MULTICAST_HEURISTIC:
        return multicast_heuristic
    elif type == SingleTrackOptimizerType.INTEGER_LINEAR_PROGRAMMING:
        return get_optimal_topology_for_a_single_track
    elif type == SingleTrackOptimizerType.MINIMUM_SPANNING_TREE:
        return minimum_spanning_tree
    else:
        raise ValueError("Invalid optimizer type.")


class MultiTrackSolution:
    def __init__(self, explicit_success, solutions: dict[str, SingleTrackSolution]):
        self.explicit_success = explicit_success
        self.solutions = solutions

    @property
    def success(self) -> bool:
        return self.explicit_success and all(solution.success for solution in self.solutions.values())

    @property
    def cost(self) -> float:
        if not self.explicit_success:
            return 0.0
        return sum(solution.cost for solution in self.solutions.values())
    
    @property
    def max_delay(self) -> float:
        if not self.explicit_success:
            return 0.0
        max_delay = max(solution.max_delay for solution in self.solutions.values())
        return max_delay

    @property
    def used_links_per_track(self) -> dict[str, list[tuple[str, str]]]:
        if not self.explicit_success:
            return {}
        return {track_id: solution.used_links for track_id, solution in self.solutions.items()}

    def __iter__(self):
        yield from (self.success, self.cost, self.max_delay, self.used_links_per_track)

    @staticmethod
    def found(solutions: dict[str, SingleTrackSolution]) -> 'MultiTrackSolution':
        return MultiTrackSolution(True, solutions)

    @staticmethod
    def not_found() -> 'MultiTrackSolution':
        return MultiTrackSolution(False, {})


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
                    f"y_{track_id}_({link[0]},{link[1]})>=x_{track_id}_{stream}_({link[0]},{link[1]})"

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
                    f"z_{track_id}_{stream}_({link[0]},{link[1]})*M>=x_{track_id}_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(zftij * dij) <= Dt
    for track_id, track in tracks.items():
        for stream in track.streams.keys():
            prob += lp.lpSum([selected_links[track_id][stream][(node1, node2)] * data["latency"]
                              for node1, node2, data in network.edges(data=True)]) <= track.delay_budget, \
                f"delay_budget_for_{track_id}_{stream}"

    prob.solve(lp.PULP_CBC_CMD(msg=False))

    success = prob.status == lp.LpStatusOptimal
    if not success:
        return MultiTrackSolution.not_found()

    solutions = {}
    for track_id, track in tracks.items():
        used_links = [link for link, var in link_usages[track_id].items() if var.varValue > 0]
        
        objective = 0.0
        for link in used_links:
            objective += network.get_edge_data(*link)["cost"]

        max_delay = max(track.delay_budget + prob.constraints[f"delay_budget_for_{track_id}_{stream}"].value() for stream in track.streams.keys())

        solutions[track_id] = SingleTrackSolution.found(objective, max_delay, used_links)

    return MultiTrackSolution.found(solutions)


def multi_to_single_track_adapter_factory(strategy: Callable[[nx.DiGraph, Track], SingleTrackSolution]) -> Callable[[nx.DiGraph, Track], MultiTrackSolution]:

    def multi_to_single_track_adapter(network: nx.DiGraph, tracks: dict[str, Track]) -> MultiTrackSolution:
        solutions = {}

        for track_id, track in tracks.items():
            solution = strategy(network, track)
            if not solution.success:
                return MultiTrackSolution.not_found()
            solutions[track_id] = solution

        return MultiTrackSolution.found(solutions)

    return multi_to_single_track_adapter


class MultiTrackOptimizerType(str, Enum):
    NATIVE = "native"
    ADAPTED = "adapted"


def get_multi_track_optimizer(type: str, **kwargs) -> Callable[[nx.DiGraph, dict[str, Track], bool], MultiTrackSolution]:
    if type == MultiTrackOptimizerType.ADAPTED:
        single_track_optimizer = kwargs.get("single_track_optimizer")
        if single_track_optimizer is None:
            raise ValueError(
                "Single track optimizer must be provided for adapted optimization.")
        return multi_to_single_track_adapter_factory(single_track_optimizer)
    elif type == MultiTrackOptimizerType.NATIVE:
        return get_optimal_topology_for_multiple_tracks
    else:
        raise ValueError("Invalid optimizer type.")
