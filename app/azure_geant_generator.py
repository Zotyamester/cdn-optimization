from overlay_underlay import create_overlay_network, create_underlay_network, create_virtual_to_physical_mapping, load_base_network
from model import default_calculate_latency, display_triangle_inequality_satisfaction, load_geant_json
from sample import store_network


if __name__ == "__main__":
    azure_nodes = [
        # North America
        ("eastus", {"location": (37.3719, -79.8164)}),             # Virginia
        ("eastus2", {"location": (36.6681, -78.3889)}),            # Virginia
        ("southcentralus", {"location": (29.4167, -98.5000)}),     # Texas
        ("westus2", {"location": (47.233, -119.852)}),             # Washington
        ("westus3", {"location": (33.4242, -111.928)}),            # Arizona
        ("centralus", {"location": (41.5908, -93.6208)}),          # Iowa
        ("northcentralus", {"location": (41.8819, -87.6278)}),     # Illinois
        ("canadacentral", {"location": (43.6532, -79.3832)}),      # Toronto, Ontario
        ("canadaeast", {"location": (46.8139, -71.2082)}),         # Quebec City, Quebec

        # South America
        ("brazilsouth", {"location": (-23.5505, -46.6333)}),       # Sao Paulo

        # Europe
        ("northeurope", {"location": (53.3478, -6.2597)}),         # Dublin, Ireland
        ("westeurope", {"location": (52.3667, 4.8945)}),           # Amsterdam, Netherlands
        ("uksouth", {"location": (51.5074, -0.1278)}),             # London, England
        ("ukwest", {"location": (53.4808, -2.2426)}),              # Manchester, England
        ("francecentral", {"location": (46.6034, 1.8883)}),        # Paris
        ("francesouth", {"location": (43.6108, 3.8772)}),          # Marseille
        ("germanywestcentral", {"location": (50.1109, 8.6821)}),   # Frankfurt
        ("germanynorth", {"location": (53.5511, 9.9937)}),         # Hamburg
        ("swedencentral", {"location": (59.3293, 18.0686)}),       # Stockholm
        ("norwayeast", {"location": (59.9139, 10.7522)}),          # Oslo
        ("norwaywest", {"location": (58.9690, 5.7331)}),           # Stavanger
        ("polandcentral", {"location": (52.2297, 21.0122)}),       # Warsaw
        ("switzerlandnorth", {"location": (47.3769, 8.5417)}),     # Zurich
        ("switzerlandwest", {"location": (46.2044, 6.1432)}),      # Geneva
        ("italynorth", {"location": (45.4642, 9.1900)}),           # Milan

        # Asia Pacific
        ("australiaeast", {"location": (-33.8688, 151.2093)}),     # Sydney
        ("australiasoutheast", {"location": (-37.8136, 144.9631)}),# Melbourne
        ("southeastasia", {"location": (1.3521, 103.8198)}),       # Singapore
        ("eastasia", {"location": (22.3964, 114.1095)}),           # Hong Kong
        ("japaneast", {"location": (35.682839, 139.759455)}),      # Tokyo
        ("japanwest", {"location": (34.6937, 135.5023)}),          # Osaka
        ("koreacentral", {"location": (37.5665, 126.9780)}),       # Seoul
        ("koreasouth", {"location": (35.1796, 129.0756)}),         # Busan
        ("centralindia", {"location": (18.5204, 73.8567)}),        # Pune
        ("southindia", {"location": (12.9716, 77.5946)}),          # Bangalore
        ("westindia", {"location": (19.0760, 72.8777)}),           # Mumbai
        ("jioindiacentral", {"location": (19.2183, 72.9781)}),     # Mumbai (Jio)
        ("jioindiawest", {"location": (18.5972, 73.7556)}),        # Pune (Jio)
        ("australiacentral", {"location": (-35.2820, 149.1286)}),  # Canberra
        ("australiacentral2", {"location": (-35.2820, 149.1286)}), # Canberra

        # Africa
        ("southafricanorth", {"location": (-26.2041, 28.0473)}),   # Johannesburg
        ("southafricawest", {"location": (-33.9249, 18.4241)}),    # Cape Town

        # Middle East
        ("uaenorth", {"location": (25.276987, 55.296249)}),        # Dubai
        ("uaecentral", {"location": (24.453884, 54.377343)}),      # Abu Dhabi
        ("israelcentral", {"location": (31.0461, 34.8516)}),       # Tel Aviv
        ("qatarcentral", {"location": (25.2760, 51.5219)}),        # Doha
    ]

    base_network = load_base_network(load_geant_json("./datasource/geant.json"), "GEANT")
    underlay_network = create_underlay_network(base_network, azure_nodes)
    mapping = create_virtual_to_physical_mapping(underlay_network, azure_nodes)
    overlay_network = create_overlay_network(underlay_network, azure_nodes, mapping)
    network = overlay_network
    display_triangle_inequality_satisfaction(network)

    answer = input("Re-calculate latency based solely on the overlay network? [y/N]: ")
    if answer.lower() == "y":
        for edge in network.edges:
            node1, node2 = edge
            network.edges[edge]["latency"] = default_calculate_latency(network, node1, node2)
        display_triangle_inequality_satisfaction(network)

    store_network(network, "./datasource/azure_geant_topo.yaml")
