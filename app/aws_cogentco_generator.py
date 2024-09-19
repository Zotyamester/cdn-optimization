from overlay_underlay import create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping, load_base_network
from model import display_triangle_inequality_satisfaction, load_graphml
from sample import store_network


if __name__ == "__main__":
    aws_nodes = [
        # European nodes
        ("eu-west-1",    {"location": (53.3498, -6.2603)}),    # Dublin, IE
        ("eu-west-2",    {"location": (51.5074, -0.1278)}),    # London, GB
        ("eu-west-3",    {"location": (48.8566, 2.3522)}),     # Paris, FR
        ("eu-central-1", {"location": (50.1109, 8.6821)}),     # Frankfurt, DE
        ("eu-north-1",   {"location": (59.3293, 18.0686)}),    # Stockholm, SE
        ("eu-south-1",   {"location": (45.4642, 9.1900)}),     # Milan, IT
        # American nodes
        ("us-east-1",    {"location": (39.0481, -77.4729)}),   # Northern Virginia, US
        ("us-west-1",    {"location": (37.7749, -122.4194)}),  # San Francisco, US
        ("us-west-2",    {"location": (45.5231, -122.6765)}),  # Oregon, US
    ]

    base_network = load_base_network(load_graphml("./datasource/Cogentco.graphml"), "Cogentco")
    underlay_network = create_underlay_network(base_network, aws_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, aws_nodes)
    overlay_network = create_overlay_network(underlay_network, aws_nodes, mapping)
    network = overlay_network
    display_triangle_inequality_satisfaction(network)
    store_network(network, "./datasource/aws_cogentco_topo.yaml")
