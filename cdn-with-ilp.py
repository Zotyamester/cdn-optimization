from dataclasses import dataclass
from typing import Tuple
import geopy.distance
import networkx as nx
import itertools
import pulp as lp
import matplotlib.pyplot as plt

@dataclass
class Node:
    location: Tuple[float, float]  # (latitude, longitude)
    cost_factor: float
    
    def __iter__(self):
        yield from (self.location, self.cost_factor)

nodes = {
    "eu-west-1":    Node((53.3498, -6.2603), 1.08),     # Dublin, Ireland
    "eu-west-2":    Node((51.5074, -0.1278), 1.26),     # London, UK
    "eu-west-3":    Node((48.8566, 2.3522), 1.08),      # Paris, France
    "eu-central-1": Node((50.1109, 8.6821), 1.08),      # Frankfurt, Germany
    "eu-north-1":   Node((59.3293, 18.0686), 0.094),    # Stockholm, Sweden
    "eu-south-1":   Node((45.4642, 9.1900), 1.08),      # Milan, Italy
    "Aalborg":      Node((57.0169, 9.9891), 0.15),      # Aalborg, Denmark
    "Budapest":     Node((47.4732, 19.0379), 0.0029)    # Budapest, Hungary
}


@dataclass
class Stream:
    name: str
    delay_budget: int
    node_reliabilities: dict

    def __iter__(self):
        yield from (self.name, self.delay_budget, self.node_reliabilities)

streams = {
    "f1": Stream(
        "Gajdos Összes Rövidítve",
        100,  # 100 ms delay budget
        {
            "eu-west-1": 0,
            "eu-west-2": 0,
            "eu-west-3": 0,
            "eu-central-1": 0,
            "eu-north-1": 0,
            "eu-south-1": 0,
            "Aalborg": -1,  # Aalborg is a publisher
            "Budapest": 1,  # Budapest is a subscriber
        }
    )
}

@dataclass
class Link:
    latency: float
    cost: float

    def __iter__(self):
        yield from (self.latency, self.cost)

links = {}

# Calculate distance between every pair of cities and add a link
LINK_PROPAGATION_SPEED = 200_000  # in km/s

for node1, node2 in itertools.combinations(nodes.keys(), 2):
    coords1 = nodes[node1].location
    coords2 = nodes[node2].location

    distance = geopy.distance.geodesic(coords1, coords2).km
    latency_in_s = distance / LINK_PROPAGATION_SPEED
    latency_in_ms = latency_in_s * 1000
    
    cost_factor1 = nodes[node1].cost_factor
    cost_factor2 = nodes[node2].cost_factor

    link_usage_cost = (cost_factor1 + cost_factor2) / 2

    # Links are unidirectional, but there is a link in both ways with the same latency and usage cost
    links[(node1, node2)] = links[(node2, node1)] = Link(latency_in_ms, link_usage_cost)

print("Links:")
for link, (latency, cost) in sorted(links.items(), key=lambda kv : kv[1].latency):
    print(f" * {' <-> '.join(link)}:\t\t{latency:.2f} ms\t\t{cost:.2f}")

prob = lp.LpProblem("MoQ_relay_topology_optimization", lp.LpMinimize)

# xfij == X_{flow}_{link}; xfij >= 0 constraint is always satisfied
transmission_bitrates = lp.LpVariable.dicts("x", (streams.keys(), links.keys()), 0, None, cat=lp.LpInteger)

# yij == Y_{link}; yij >= 0 constraint is always satisfied
link_usages = lp.LpVariable.dicts("y", links.keys(), 0, None, cat=lp.LpInteger)

# Objective function
prob += lp.lpSum([cost * link_usages[link] for link, (_, cost) in links.items()]), "total_link_usage"

# Constraint: yij >= xfij
for flow in streams.keys():
    for link in links.keys():
        prob += link_usages[link] >= transmission_bitrates[flow][link], f"y_({link[0]},{link[1]})>=x_{flow}_({link[0]},{link[1]})"

# Constraint: sum(xfji) - sum(xfij) == Rfi
for flow, (_, _, node_reliabilities) in streams.items():
    for node in nodes.keys():
        # Devlog: This constraint causes problems when using undirected graphs.
        #         The graph should obviously be directed, since otherwise "in-going" and "out-going"
        #         traffic will be indistinguishable, and as such, the equation might not hold.
        in_going = lp.lpSum([transmission_bitrates[flow][link] for link in links.keys() if link[1] == node])
        out_going = lp.lpSum([transmission_bitrates[flow][link] for link in links.keys() if link[0] == node])
        prob += in_going - out_going == node_reliabilities[node], f"nodal_balance_for_{flow}_{node}"

# Solve the LP
prob.solve(lp.PULP_CBC_CMD(msg=False))

# Print the results
print(lp.LpStatus[prob.status])
for var in prob.variables():
    value = int(var.varValue)
    if value > 0:
        print(f" - {var.name} = {value}")

print("Constraints:")
for constraint in prob.constraints.values():
    if constraint.value() != 0:
        print(f" - {constraint.name}: {constraint.value()}")

used_links = [link for link, var in link_usages.items() if var.varValue > 0]

# Plot the network
g = nx.Graph()

for node, (location, cost_factor) in nodes.items():
    g.add_node(node, location=location, cost_factor=cost_factor)
for link, (latency, cost) in links.items():
    g.add_edge(*link, latency=latency, cost=cost)

plt.figure(figsize=(16, 10))
node_positions = {node_name: node_attrs["location"] for node_name, node_attrs in g.nodes.data()}
nx.draw_networkx(g, pos=node_positions, node_size=4000, font_size=10, font_color="white")
nx.draw_networkx_edges(g, pos=node_positions, edgelist=used_links, edge_color="red", width=2)

plt.axis("off")
plt.show()
