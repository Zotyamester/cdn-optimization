import pulp as lp

from model import Network, Track


def get_optimal_topology_for_multiple_tracks(network: Network, tracks: dict[str, Track], debug: bool = False) -> tuple[int, dict[str, list[tuple[str, str]]]]:
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
            prob += lp.lpSum([selected_links[track_id][stream][link] * latency
                              for link, (latency, _) in network.links.items()]) <= delay_budget, \
                f"delay_budget_for_{track_id}_{stream}"

    prob.solve(lp.PULP_CBC_CMD(msg=False))

    status = prob.status

    if debug:
        print(f"Solution: {lp.LpStatus[status]}")
        print()

        print("Variables:")
        for var in prob.variables():
            value = int(var.varValue)
            if value > 0:
                print(f" - {var.name} = {value}")
        print()

        print("Constraints:")
        for constraint in prob.constraints.values():
            if constraint.value() != 0:
                print(f" - {constraint.name}: {constraint.value()}")
        print()

    used_links_per_track = {}
    for track_id in tracks.keys():
        used_links_per_track[track_id] = [
            link for link, var in link_usages[track_id].items() if var.varValue > 0]
    return status, used_links_per_track
