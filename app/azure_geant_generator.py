from overlay_underlay import create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping, load_base_network
from model import display_triangle_inequality_satisfaction, load_geant_json
from sample import store_network


if __name__ == "__main__":
    azure_nodes = [
        # European nodes
        ("North_Europe", {"location": (53.3478, -6.2597)}),         # Dublin, IE
        ("UK_South", {"location": (51.5074, -0.1278)}),             # London, GB
        ("France_Central", {"location": (48.8566, 2.3522)}),        # Paris, FR
        ("Germany_West_Central", {"location": (50.1109, 8.6821)}),  # Frankfurt, DE
        ("Sweden_Central", {"location": (59.3293, 18.0686)}),       # Stockholm, SE
        ("Switzerland_North", {"location": (47.3769, 8.5417)}),     # Zurich, CH
        # American nodes
        ("East_US", {"location": (37.9269, -78.0240)}),             # Virginia, US
        ("West_US", {"location": (37.7749, -122.4194)}),            # San Francisco, US
        ("Central_US", {"location": (41.8781, -87.6298)}),          # Chicago, US
        ("West_US_2", {"location": (45.5122, -122.6587)}),          # Oregon, US
    ]

    base_network = load_base_network(load_geant_json("./datasource/geant.json"), "GEANT")
    underlay_network = create_underlay_network(base_network, azure_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, azure_nodes)
    overlay_network = create_overlay_network(underlay_network, azure_nodes, mapping)
    network = overlay_network
    display_triangle_inequality_satisfaction(network)
    store_network(network, "./datasource/azure_geant_topo.yaml")
