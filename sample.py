from model import Network, Node


nodes = {
    # European nodes
    "eu-west-1":    Node((53.3498, -6.2603)),     # Dublin, IE
    "eu-west-2":    Node((51.5074, -0.1278)),     # London, GB
    "eu-west-3":    Node((48.8566, 2.3522)),      # Paris, FR
    "eu-central-1": Node((50.1109, 8.6821)),      # Frankfurt, DE
    "eu-north-1":   Node((59.3293, 18.0686)),    # Stockholm, SE
    "eu-south-1":   Node((45.4642, 9.1900)),      # Milan, IT
    "Aalborg":      Node((57.0169, 9.9891)),      # Aalborg, DK
    "Budapest":     Node((47.4732, 19.0379)),    # Budapest, HU

    # Other nodes
    "us-east-1":    Node((39.0481, -77.4729)),    # Northern Virginia, US
    "us-west-1":    Node((37.7749, -122.4194)),   # San Francisco, US
    "us-west-2":    Node((45.5231, -122.6765)),   # Oregon, US
}

link_costs = {
    ("eu-west-1", "eu-west-2"): 0.02,  # Dublin to London
    ("eu-west-1", "eu-west-3"): 0.03,  # Dublin to Paris
    ("eu-west-1", "eu-central-1"): 0.04,  # Dublin to Frankfurt
    ("eu-west-1", "eu-north-1"): 0.05,  # Dublin to Stockholm
    ("eu-west-1", "eu-south-1"): 0.06,  # Dublin to Milan
    ("eu-west-1", "Aalborg"): 0.07,  # Dublin to Aalborg
    ("eu-west-1", "Budapest"): 0.08,  # Dublin to Budapest
    ("eu-west-1", "us-east-1"): 0.09,  # Dublin to Northern Virginia
    ("eu-west-1", "us-west-1"): 0.10,  # Dublin to San Francisco
    ("eu-west-1", "us-west-2"): 0.11,  # Dublin to Oregon

    ("eu-west-2", "eu-west-3"): 0.02,  # London to Paris
    ("eu-west-2", "eu-central-1"): 0.03,  # London to Frankfurt
    ("eu-west-2", "eu-north-1"): 0.04,  # London to Stockholm
    ("eu-west-2", "eu-south-1"): 0.05,  # London to Milan
    ("eu-west-2", "Aalborg"): 0.06,  # London to Aalborg
    ("eu-west-2", "Budapest"): 0.07,  # London to Budapest
    ("eu-west-2", "us-east-1"): 0.08,  # London to Northern Virginia
    ("eu-west-2", "us-west-1"): 0.09,  # London to San Francisco
    ("eu-west-2", "us-west-2"): 0.10,  # London to Oregon

    ("eu-west-3", "eu-central-1"): 0.02,  # Paris to Frankfurt
    ("eu-west-3", "eu-north-1"): 0.03,  # Paris to Stockholm
    ("eu-west-3", "eu-south-1"): 0.04,  # Paris to Milan
    ("eu-west-3", "Aalborg"): 0.05,  # Paris to Aalborg
    ("eu-west-3", "Budapest"): 0.06,  # Paris to Budapest
    ("eu-west-3", "us-east-1"): 0.07,  # Paris to Northern Virginia
    ("eu-west-3", "us-west-1"): 0.08,  # Paris to San Francisco
    ("eu-west-3", "us-west-2"): 0.09,  # Paris to Oregon

    ("eu-central-1", "eu-north-1"): 0.02,  # Frankfurt to Stockholm
    ("eu-central-1", "eu-south-1"): 0.03,  # Frankfurt to Milan
    ("eu-central-1", "Aalborg"): 0.04,  # Frankfurt to Aalborg
    ("eu-central-1", "Budapest"): 0.05,  # Frankfurt to Budapest
    ("eu-central-1", "us-east-1"): 0.06,  # Frankfurt to Northern Virginia
    ("eu-central-1", "us-west-1"): 0.07,  # Frankfurt to San Francisco
    ("eu-central-1", "us-west-2"): 0.08,  # Frankfurt to Oregon

    ("eu-north-1", "eu-south-1"): 0.02,  # Stockholm to Milan
    ("eu-north-1", "Aalborg"): 0.03,  # Stockholm to Aalborg
    ("eu-north-1", "Budapest"): 0.04,  # Stockholm to Budapest
    ("eu-north-1", "us-east-1"): 0.05,  # Stockholm to Northern Virginia
    ("eu-north-1", "us-west-1"): 0.06,  # Stockholm to San Francisco
    ("eu-north-1", "us-west-2"): 0.07,  # Stockholm to Oregon

    ("eu-south-1", "Aalborg"): 0.02,  # Milan to Aalborg
    ("eu-south-1", "Budapest"): 0.03,  # Milan to Budapest
    ("eu-south-1", "us-east-1"): 0.04,  # Milan to Northern Virginia
    ("eu-south-1", "us-west-1"): 0.05,  # Milan to San Francisco
    ("eu-south-1", "us-west-2"): 0.06,  # Milan to Oregon

    ("Aalborg", "Budapest"): 0.04,  # Aalborg to Budapest
    ("Aalborg", "us-east-1"): 0.03,  # Aalborg to Northern Virginia
    ("Aalborg", "us-west-1"): 0.04,  # Aalborg to San Francisco
    ("Aalborg", "us-west-2"): 0.05,  # Aalborg to Oregon

    ("Budapest", "us-east-1"): 0.02,  # Budapest to Northern Virginia
    ("Budapest", "us-west-1"): 0.03,  # Budapest to San Francisco
    ("Budapest", "us-west-2"): 0.04,  # Budapest to Oregon

    ("us-east-1", "us-west-1"): 0.02,  # Northern Virginia to San Francisco
    ("us-east-1", "us-west-2"): 0.03,  # Northern Virginia to Oregon

    ("us-west-1", "us-west-2"): 0.02,  # San Francisco to Oregon
}


def calculate_cost(_, node1, node2):
    global link_costs
    link = (node1, node2)
    if link in link_costs:
        return link_costs[link]
    reverse_link = (node2, node1)
    if reverse_link in link_costs:
        return link_costs[reverse_link]
    raise ValueError(f"Link cost not found for {link} or {reverse_link}")


network = Network(nodes, calculate_cost)

if __name__ == "__main__":
    triangle_inequality_satisfied = 0

    for start_node in nodes.keys():
        for end_node in nodes.keys():
            if end_node == start_node:
                continue

            for intermediate_node in nodes.keys():
                if intermediate_node == start_node or intermediate_node == end_node:
                    continue

                cost1 = calculate_cost(nodes, start_node, intermediate_node)
                cost2 = calculate_cost(nodes, intermediate_node, end_node)
                cost_direct = calculate_cost(nodes, start_node, end_node)

                print(f"{start_node} -> {intermediate_node} -> {end_node}")
                if cost1 + cost2 >= cost_direct:
                    print("\tOK")
                    triangle_inequality_satisfied += 1
                else:
                    print("\nFAIL")

    n = len(nodes)
    total = n * (n - 1) * (n - 2)  # n choose 3 * 3! => variation
    print(f"{triangle_inequality_satisfied} / {total} satisfied.")
