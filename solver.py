import dataclasses
import itertools
import math
from typing import Callable
import pulp as lp
from model import Network, Track


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


def get_optimal_topology_for_a_single_track(network: Network, track: Track) -> SingleTrackSolution:
    prob = lp.LpProblem("MoQ_relay_topology_optimization", lp.LpMinimize)

    # xfij == x_{stream}_{link}; xfij >= 0 constraint is always satisfied
    transmission_bitrates = lp.LpVariable.dicts(
        "x", (track.streams.keys(), network.links.keys()), 0, None, cat=lp.LpContinuous)

    # yij == y_{link}; yij >= 0 constraint is always satisfied
    link_usages = lp.LpVariable.dicts(
        "y", network.links.keys(), 0, None, cat=lp.LpContinuous)

    # zfij == z_{stream}_{link}; zij == 0 or 1
    selected_links = lp.LpVariable.dicts(
        "z", (track.streams.keys(), network.links.keys()), 0, 1, cat=lp.LpBinary)

    # Objective function
    prob += lp.lpSum([cost * link_usages[link] for link, (_, cost)
                      in network.links.items()]), "total_link_usage"

    # Constraint: yij >= xfij
    for stream in track.streams.keys():
        for link in network.links.keys():
            prob += link_usages[link] >= transmission_bitrates[stream][link], \
                f"y_({link[0]},{link[1]})>=x_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(xfji) - sum(xfij) == Rfi
    for stream, (_, node_reliabilities) in track.streams.items():
        for node in network.nodes.keys():
            # Devlog: This constraint causes problems when using undirected graphs.
            #         The graph should obviously be directed, since otherwise "in-going" and "out-going"
            #         traffic will be indistinguishable, and as such, the equation might not hold.
            in_going = lp.lpSum([transmission_bitrates[stream][link]
                                for link in network.links.keys() if link[1] == node])
            out_going = lp.lpSum([transmission_bitrates[stream][link]
                                  for link in network.links.keys() if link[0] == node])
            prob += in_going - out_going == node_reliabilities[node], \
                f"nodal_balance_for_{stream}_{node}"

    # Constraint: zfij*M >= xfij
    M = 1e4  # Some large number
    for stream in track.streams.keys():
        for link in network.links.keys():
            prob += selected_links[stream][link] * M >= transmission_bitrates[stream][link], \
                f"z_{stream}_({link[0]},{
                link[1]})*M>=x_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(zfij * dij) <= Df
    for stream, (delay_budget, _) in track.streams.items():
        prob += lp.lpSum([selected_links[stream][link] * e2e_latency
                          for link, (e2e_latency, _) in network.links.items()]) <= delay_budget, \
            f"delay_budget_for_{stream}"

    prob.solve(lp.PULP_CBC_CMD(msg=False))

    success = prob.status == lp.LpStatusOptimal
    if not success:
        return SingleTrackSolution.not_found()

    objective = prob.objective.value()
    used_links = [link for link, var in link_usages.items()
                  if var.varValue > 0]
    return SingleTrackSolution.found(objective, used_links)


def find_cheapest_link_with_delay_constraint(network: Network, track: Track, tree_nodes: set[str], tree_latencies: dict[str, float]) -> tuple[str, str] | None:
    best_link = None
    best_cost = math.inf
    
    for node1 in tree_nodes:
        for node2 in network.nodes.keys():
            if node2 not in tree_nodes:
                link = (node1, node2)
                latency, cost = network.links[link]
                e2e_latency = tree_latencies[node1] + latency
                if e2e_latency < track._subscribers[node2] and cost < best_cost:
                    best_link = (node1, node2)
                    best_cost = cost

    return best_link


def find_link_with_max_delay_relaxation(network: Network, track: Track, tree_nodes: set[str], tree_latencies: dict[str, float]) -> tuple[str, str] | None:
    best_link = None
    max_relaxation = 0.0
    
    for link in itertools.combinations(tree_nodes, 2):
        node1, node2 = link
        latency, _ = network.links[link]

        new_e2e_latency = tree_latencies[node1] + latency
        old_e2e_latency = tree_latencies[node2]

        relaxation = old_e2e_latency - new_e2e_latency
        if relaxation > max_relaxation:
            best_link = link
            max_relaxation = relaxation

    return best_link


def bdb_for_a_single_track(network: Network, track: Track) -> SingleTrackSolution:
    tree_nodes = {track._publisher}
    tree_edges = set()
    tree_latencies = {track._publisher: 0}
    tree_cost = 0.0

    # Phase 1: Construct a suboptimal delay-constrained spanning tree

    while len(tree_nodes) < len(network.nodes):
        if (link := find_cheapest_link_with_delay_constraint(network, track, tree_nodes, tree_latencies)) is not None:
            node1, node2 = link
            latency, cost = network.links[link]

            tree_nodes.add(node2)
            tree_edges.add(link)
            tree_latencies[node2] = tree_latencies[node1] + latency
            tree_cost += cost
        elif (new_link := find_link_with_max_delay_relaxation(network, track, tree_nodes, tree_latencies)) is not None:
            # Remove & clean up after the old link
            old_link = next(filter(lambda link, end_node=node2: link[1] == end_node, tree_edges))
            _, old_cost = network.links[old_link]

            tree_edges.remove(old_link)
            tree_cost -= old_cost

            # Add the new link & update the tree
            node1, node2 = new_link
            new_latency, new_cost = network.links[new_link]

            tree_edges.add(new_link)
            tree_latencies[node2] = tree_latencies[node1] + new_latency
            tree_cost += new_cost

            # Update the tree latencies (in a BFS fashion)
            update_queue = {node2}
            while len(update_queue) > 0:
                node = update_queue.pop()
                for link in tree_edges:
                    if link[0] == node:
                        next_node = link[1]
                        tree_latencies[next_node] = tree_latencies[node] + network.links[link].latency
                        update_queue.add(next_node)
        else:
            return SingleTrackSolution.not_found()
    
    # Phase 2: Optimize the tree by replacing edges using heuristics

    # TODO: Implement the heuristic
    # while True:
    #     link = find_cheapest_augmenting_link_with_delay_constraint(network, track, tree_nodes, tree_latencies)
    #     if contains_directed_loop(track._publisher, tree_edges):
    #         link_to_remove, link_to_add = find_replacement_pair_in_directed_loop(network, track, tree_nodes, tree_latencies)
    #         if link_to_remove is None or link_to_add is None:
    #             break
    #         tree_edges.remove(link_to_remove)
    #         tree_edges.add(link_to_add)
    #         tree_cost += network.links[link_to_add].cost - network.links[link_to_remove].cost

    return SingleTrackSolution.found(tree_cost, list(tree_edges))


def multi_to_single_track_adapter(network: Network, tracks: dict[str, Track]) -> MultiTrackSolution:
    objective = 0.0
    used_links_per_track = {}
    for track_id, track in tracks.items():
        track_success, track_objective, used_links = get_optimal_topology_for_a_single_track(
            network, track)
        if not track_success:
            return MultiTrackSolution.not_found()

        objective += track_objective
        used_links_per_track[track_id] = used_links
    return MultiTrackSolution.found(objective, used_links_per_track)


def get_optimal_topology_for_multiple_tracks(network: Network, tracks: dict[str, Track]) -> MultiTrackSolution:
    prob = lp.LpProblem("MoQ_relay_topology_optimization", lp.LpMinimize)

    # xftij == x_{track}_{stream}_{link}; xftij >= 0 constraint is always satisfied
    transmission_bitrates = {}
    for track_id, track in tracks.items():
        transmission_bitrates[track_id] = lp.LpVariable.dicts(
            f"x_{track_id}", (track.streams.keys(), network.links.keys()), 0, None, cat=lp.LpContinuous)

    # ytij == y_{track}_{link}; ytij >= 0 constraint is always satisfied
    link_usages = lp.LpVariable.dicts(
        "y", (tracks.keys(), network.links.keys()), 0, None, cat=lp.LpContinuous)

    # zftij == z_{track}_{stream}_{link}; ztij == 0 or 1
    selected_links = {}
    for track_id, track in tracks.items():
        selected_links[track_id] = lp.LpVariable.dicts(
            f"z_{track_id}", (track.streams.keys(), network.links.keys()), 0, 1, cat=lp.LpBinary)

    # Objective function
    prob += lp.lpSum([cost * link_usages[track_id][link] for link, (_, cost)
                     in network.links.items() for track_id in tracks.keys()]), "total_link_usage"

    # Constraint: ytij >= xftij
    for track_id, track in tracks.items():
        for stream in track.streams.keys():
            for link in network.links.keys():
                prob += link_usages[track_id][link] >= transmission_bitrates[track_id][stream][link], \
                    f"y_{track_id}_({link[0]},{link[1]})>=x_{track_id}_{
                    stream}_({link[0]},{link[1]})"

    # Constraint: sum(xftji) - sum(xftij) == Rfti
    for track_id, track in tracks.items():
        for stream, (_, node_reliabilities) in track.streams.items():
            for node in network.nodes.keys():
                # Devlog: This constraint causes problems when using undirected graphs.
                #         The graph should obviously be directed, since otherwise "in-going" and "out-going"
                #         traffic will be indistinguishable, and as such, the equation might not hold.
                in_going = lp.lpSum([transmission_bitrates[track_id][stream][link]
                                    for link in network.links.keys() if link[1] == node])
                out_going = lp.lpSum([transmission_bitrates[track_id][stream][link]
                                      for link in network.links.keys() if link[0] == node])
                prob += in_going - out_going == node_reliabilities[node], \
                    f"nodal_balance_for_{track_id}_{stream}_{node}"

    # Constraint: zftij*M >= xftij
    M = 1e4  # Some large number
    for track_id, track in tracks.items():
        for stream in track.streams.keys():
            for link in network.links.keys():
                prob += selected_links[track_id][stream][link] * M >= transmission_bitrates[track_id][stream][link], \
                    f"z_{track_id}_{stream}_({link[0]},{
                    link[1]})*M>=x_{track_id}_{stream}_({link[0]},{link[1]})"

    # Constraint: sum(zftij * dij) <= Dft
    for track_id, track in tracks.items():
        for stream, (delay_budget, _) in track.streams.items():
            prob += lp.lpSum([selected_links[track_id][stream][link] * e2e_latency
                              for link, (e2e_latency, _) in network.links.items()]) <= delay_budget, \
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


def get_multi_track_optimizer(type: str) -> Callable[[Network, dict[str, Track], bool], MultiTrackSolution]:
    if type == "single":
        return multi_to_single_track_adapter
    elif type == "multiple":
        return get_optimal_topology_for_multiple_tracks
    else:
        raise ValueError("Invalid optimizer type.")
