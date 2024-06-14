import pulp as lp

from model import Network, Track


def get_optimal_topology(network: Network, track: Track, debug: bool = False) -> tuple[int, list[tuple[str, str]]]:
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
        prob += lp.lpSum([selected_links[stream][link] * latency
                          for link, (latency, _) in network.links.items()]) <= delay_budget, \
            f"delay_budget_for_{stream}"

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

    used_links = [link for link, var in link_usages.items()
                  if var.varValue > 0]
    return status, used_links
