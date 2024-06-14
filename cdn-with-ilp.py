import pulp as lp
from model import Network, Node, Track, display_network_links, display_track_stats
from plot import plot_network

# Sample network and track ***************************************************************************************

nodes = {
    "eu-west-1":    Node((53.3498, -6.2603), 1.08),     # Dublin, IE
    "eu-west-2":    Node((51.5074, -0.1278), 1.26),     # London, GB
    "eu-west-3":    Node((48.8566, 2.3522), 1.08),      # Paris, FR
    "eu-central-1": Node((50.1109, 8.6821), 1.08),      # Frankfurt, DE
    "eu-north-1":   Node((59.3293, 18.0686), 0.094),    # Stockholm, SE
    "eu-south-1":   Node((45.4642, 9.1900), 1.08),      # Milan, IT
    "Aalborg":      Node((57.0169, 9.9891), 0.15),      # Aalborg, DK
    "Budapest":     Node((47.4732, 19.0379), 0.0029)    # Budapest, HU
}

network = Network(nodes)
display_network_links(network)

# Change {0}'s delay budget to {1}, and see how the solution changes!
#  * eu-north-1, 17
#  * eu-south-1, 11
#  * eu-south-1, 12
#  * eu-south-1, 14
#  * eu-south-1, 18
track = Track("Gajdos Összes Rövidítve", "eu-central-1",
              [("Budapest", 95), ("Aalborg", 5), ("eu-north-1", 16), ("eu-south-1", 11)])
tracks = [track]
display_track_stats(nodes, tracks)

# Linear Programming *********************************************************************************************

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

print(f"Solution: {lp.LpStatus[prob.status]}")
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

used_links = [link for link, var in link_usages.items() if var.varValue > 0]

# Plot the network ***********************************************************************************************

plot_network(network, used_links)
