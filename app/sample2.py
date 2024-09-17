from model import create_graph, display_triangle_inequality_satisfaction
import yaml


def make_network(file_path: str = 'datasource/small_topo.yaml'):
    with open(file_path, 'r') as file:
        topo_data = yaml.safe_load(file)

    nodes = [
        (node['name'], {'location': (node['location'][0], node['location'][1])})
        for node in topo_data['nodes']
    ]

    global link_costs
    link_costs = {}

    for edge in topo_data['edges']:
        node1 = edge['node1']
        node2 = edge['node2']
        cost = edge['attributes']['cost']
        link_costs[(node1, node2)] = cost

    return create_graph(nodes, calculate_cost=calculate_cost)

def calculate_cost(_, node1, node2):

    link = (node1, node2)
    if link in link_costs:
        return link_costs[link]
    reverse_link = (node2, node1)
    if reverse_link in link_costs:
        return link_costs[reverse_link]
    raise ValueError(f"Link cost not found for {link} or {reverse_link}")


if __name__ == "__main__":
    display_triangle_inequality_satisfaction(make_network())