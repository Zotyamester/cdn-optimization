from model import create_graph, display_triangle_inequality_satisfaction

# Hardcoded sample network based on VM-VM data transfer pricing within Google Cloud regions.

nodes = [
    # European nodes
    ("europe-west1",            {"location": (50.4791, 3.8646)}),     # St. Ghislain, BE
    ("europe-west2",            {"location": (51.5074, -0.1278)}),    # London, GB
    ("europe-west3",            {"location": (50.1109, 8.6821)}),     # Frankfurt, DE
    ("europe-north1",           {"location": (60.5697, 27.1881)}),    # Hamina, FI
    ("europe-south1",           {"location": (45.4642, 9.1900)}),     # Milan, IT

    # North American nodes
    ("northamerica-northeast1", {"location": (45.5017, -73.5673)}),   # Montreal, CA
    ("us-east1",                {"location": (33.8361, -81.1637)}),   # South Carolina, US
    ("us-west1",                {"location": (45.5946, -121.1787)}),  # The Dalles, Oregon, US
    ("us-west2",                {"location": (34.0522, -118.2437)}),  # Los Angeles, US

    # Asian nodes
    ("asia-east1",              {"location": (24.0742, 120.5624)}),   # Changhua County, TW
    ("asia-northeast1",         {"location": (35.6895, 139.6917)}),   # Tokyo, JP
    ("asia-southeast1",         {"location": (1.3521, 103.8198)}),    # Singapore, SG

    # Indonesian nodes
    ("asia-southeast2",         {"location": (-6.2088, 106.8456)}),   # Jakarta, ID

    # Oceania nodes
    ("australia-southeast1",    {"location": (-33.8651, 151.2093)}),  # Sydney, AU

    # Middle Eastern nodes
    ("asia-west1",              {"location": (19.0760, 72.8777)}),    # Mumbai, IN

    # South American nodes
    ("southamerica-east1",      {"location": (-23.5505, -46.6333)}),  # Sao Paulo, BR

    # African nodes
    ("africa-west1",            {"location": (-26.2041, 28.0473)}),   # Johannesburg, ZA
]

link_costs = {
    ("northamerica-northeast1", "us-east1"): 0.02,
    ("northamerica-northeast1", "us-west1"): 0.02,
    ("northamerica-northeast1", "us-west2"): 0.02,
    ("us-east1", "northamerica-northeast1"): 0.02,
    ("us-east1", "us-west1"): 0.02,
    ("us-east1", "us-west2"): 0.02,
    ("us-west1", "northamerica-northeast1"): 0.02,
    ("us-west1", "us-east1"): 0.02,
    ("us-west1", "us-west2"): 0.02,
    ("us-west2", "northamerica-northeast1"): 0.02,
    ("us-west2", "us-east1"): 0.02,
    ("us-west2", "us-west1"): 0.02,
    ("northamerica-northeast1", "europe-west1"): 0.05,
    ("northamerica-northeast1", "europe-west2"): 0.05,
    ("northamerica-northeast1", "europe-west3"): 0.05,
    ("northamerica-northeast1", "europe-north1"): 0.05,
    ("northamerica-northeast1", "europe-south1"): 0.05,
    ("us-east1", "europe-west1"): 0.05,
    ("us-east1", "europe-west2"): 0.05,
    ("us-east1", "europe-west3"): 0.05,
    ("us-east1", "europe-north1"): 0.05,
    ("us-east1", "europe-south1"): 0.05,
    ("us-west1", "europe-west1"): 0.05,
    ("us-west1", "europe-west2"): 0.05,
    ("us-west1", "europe-west3"): 0.05,
    ("us-west1", "europe-north1"): 0.05,
    ("us-west1", "europe-south1"): 0.05,
    ("us-west2", "europe-west1"): 0.05,
    ("us-west2", "europe-west2"): 0.05,
    ("us-west2", "europe-west3"): 0.05,
    ("us-west2", "europe-north1"): 0.05,
    ("us-west2", "europe-south1"): 0.05,
    ("northamerica-northeast1", "asia-east1"): 0.08,
    ("northamerica-northeast1", "asia-northeast1"): 0.08,
    ("northamerica-northeast1", "asia-southeast1"): 0.08,
    ("northamerica-northeast1", "asia-west1"): 0.11,
    ("us-east1", "asia-east1"): 0.08,
    ("us-east1", "asia-northeast1"): 0.08,
    ("us-east1", "asia-southeast1"): 0.08,
    ("us-east1", "asia-west1"): 0.11,
    ("us-west1", "asia-east1"): 0.08,
    ("us-west1", "asia-northeast1"): 0.08,
    ("us-west1", "asia-southeast1"): 0.08,
    ("us-west1", "asia-west1"): 0.11,
    ("us-west2", "asia-east1"): 0.08,
    ("us-west2", "asia-northeast1"): 0.08,
    ("us-west2", "asia-southeast1"): 0.08,
    ("us-west2", "asia-west1"): 0.11,
    ("northamerica-northeast1", "asia-southeast2"): 0.1,
    ("us-east1", "asia-southeast2"): 0.1,
    ("us-west1", "asia-southeast2"): 0.1,
    ("us-west2", "asia-southeast2"): 0.1,
    ("northamerica-northeast1", "australia-southeast1"): 0.1,
    ("us-east1", "australia-southeast1"): 0.1,
    ("us-west1", "australia-southeast1"): 0.1,
    ("us-west2", "australia-southeast1"): 0.1,
    ("northamerica-northeast1", "southamerica-east1"): 0.14,
    ("us-east1", "southamerica-east1"): 0.14,
    ("us-west1", "southamerica-east1"): 0.14,
    ("us-west2", "southamerica-east1"): 0.14,
    ("northamerica-northeast1", "africa-west1"): 0.11,
    ("us-east1", "africa-west1"): 0.11,
    ("us-west1", "africa-west1"): 0.11,
    ("us-west2", "africa-west1"): 0.11,
    ("europe-west1", "northamerica-northeast1"): 0.05,
    ("europe-west1", "us-east1"): 0.05,
    ("europe-west1", "us-west1"): 0.05,
    ("europe-west1", "us-west2"): 0.05,
    ("europe-west2", "northamerica-northeast1"): 0.05,
    ("europe-west2", "us-east1"): 0.05,
    ("europe-west2", "us-west1"): 0.05,
    ("europe-west2", "us-west2"): 0.05,
    ("europe-west3", "northamerica-northeast1"): 0.05,
    ("europe-west3", "us-east1"): 0.05,
    ("europe-west3", "us-west1"): 0.05,
    ("europe-west3", "us-west2"): 0.05,
    ("europe-north1", "northamerica-northeast1"): 0.05,
    ("europe-north1", "us-east1"): 0.05,
    ("europe-north1", "us-west1"): 0.05,
    ("europe-north1", "us-west2"): 0.05,
    ("europe-south1", "northamerica-northeast1"): 0.05,
    ("europe-south1", "us-east1"): 0.05,
    ("europe-south1", "us-west1"): 0.05,
    ("europe-south1", "us-west2"): 0.05,
    ("europe-west1", "europe-west2"): 0.02,
    ("europe-west1", "europe-west3"): 0.02,
    ("europe-west1", "europe-north1"): 0.02,
    ("europe-west1", "europe-south1"): 0.02,
    ("europe-west2", "europe-west1"): 0.02,
    ("europe-west2", "europe-west3"): 0.02,
    ("europe-west2", "europe-north1"): 0.02,
    ("europe-west2", "europe-south1"): 0.02,
    ("europe-west3", "europe-west1"): 0.02,
    ("europe-west3", "europe-west2"): 0.02,
    ("europe-west3", "europe-north1"): 0.02,
    ("europe-west3", "europe-south1"): 0.02,
    ("europe-north1", "europe-west1"): 0.02,
    ("europe-north1", "europe-west2"): 0.02,
    ("europe-north1", "europe-west3"): 0.02,
    ("europe-north1", "europe-south1"): 0.02,
    ("europe-south1", "europe-west1"): 0.02,
    ("europe-south1", "europe-west2"): 0.02,
    ("europe-south1", "europe-west3"): 0.02,
    ("europe-south1", "europe-north1"): 0.02,
    ("europe-west1", "asia-east1"): 0.08,
    ("europe-west1", "asia-northeast1"): 0.08,
    ("europe-west1", "asia-southeast1"): 0.08,
    ("europe-west1", "asia-west1"): 0.11,
    ("europe-west2", "asia-east1"): 0.08,
    ("europe-west2", "asia-northeast1"): 0.08,
    ("europe-west2", "asia-southeast1"): 0.08,
    ("europe-west2", "asia-west1"): 0.11,
    ("europe-west3", "asia-east1"): 0.08,
    ("europe-west3", "asia-northeast1"): 0.08,
    ("europe-west3", "asia-southeast1"): 0.08,
    ("europe-west3", "asia-west1"): 0.11,
    ("europe-north1", "asia-east1"): 0.08,
    ("europe-north1", "asia-northeast1"): 0.08,
    ("europe-north1", "asia-southeast1"): 0.08,
    ("europe-north1", "asia-west1"): 0.11,
    ("europe-south1", "asia-east1"): 0.08,
    ("europe-south1", "asia-northeast1"): 0.08,
    ("europe-south1", "asia-southeast1"): 0.08,
    ("europe-south1", "asia-west1"): 0.11,
    ("europe-west1", "asia-southeast2"): 0.1,
    ("europe-west2", "asia-southeast2"): 0.1,
    ("europe-west3", "asia-southeast2"): 0.1,
    ("europe-north1", "asia-southeast2"): 0.1,
    ("europe-south1", "asia-southeast2"): 0.1,
    ("europe-west1", "australia-southeast1"): 0.1,
    ("europe-west2", "australia-southeast1"): 0.1,
    ("europe-west3", "australia-southeast1"): 0.1,
    ("europe-north1", "australia-southeast1"): 0.1,
    ("europe-south1", "australia-southeast1"): 0.1,
    ("europe-west1", "southamerica-east1"): 0.14,
    ("europe-west2", "southamerica-east1"): 0.14,
    ("europe-west3", "southamerica-east1"): 0.14,
    ("europe-north1", "southamerica-east1"): 0.14,
    ("europe-south1", "southamerica-east1"): 0.14,
    ("europe-west1", "africa-west1"): 0.11,
    ("europe-west2", "africa-west1"): 0.11,
    ("europe-west3", "africa-west1"): 0.11,
    ("europe-north1", "africa-west1"): 0.11,
    ("europe-south1", "africa-west1"): 0.11,
    ("asia-east1", "northamerica-northeast1"): 0.08,
    ("asia-east1", "us-east1"): 0.08,
    ("asia-east1", "us-west1"): 0.08,
    ("asia-east1", "us-west2"): 0.08,
    ("asia-northeast1", "northamerica-northeast1"): 0.08,
    ("asia-northeast1", "us-east1"): 0.08,
    ("asia-northeast1", "us-west1"): 0.08,
    ("asia-northeast1", "us-west2"): 0.08,
    ("asia-southeast1", "northamerica-northeast1"): 0.08,
    ("asia-southeast1", "us-east1"): 0.08,
    ("asia-southeast1", "us-west1"): 0.08,
    ("asia-southeast1", "us-west2"): 0.08,
    ("asia-west1", "northamerica-northeast1"): 0.11,
    ("asia-west1", "us-east1"): 0.11,
    ("asia-west1", "us-west1"): 0.11,
    ("asia-west1", "us-west2"): 0.11,
    ("asia-east1", "europe-west1"): 0.08,
    ("asia-east1", "europe-west2"): 0.08,
    ("asia-east1", "europe-west3"): 0.08,
    ("asia-east1", "europe-north1"): 0.08,
    ("asia-east1", "europe-south1"): 0.08,
    ("asia-northeast1", "europe-west1"): 0.08,
    ("asia-northeast1", "europe-west2"): 0.08,
    ("asia-northeast1", "europe-west3"): 0.08,
    ("asia-northeast1", "europe-north1"): 0.08,
    ("asia-northeast1", "europe-south1"): 0.08,
    ("asia-southeast1", "europe-west1"): 0.08,
    ("asia-southeast1", "europe-west2"): 0.08,
    ("asia-southeast1", "europe-west3"): 0.08,
    ("asia-southeast1", "europe-north1"): 0.08,
    ("asia-southeast1", "europe-south1"): 0.08,
    ("asia-west1", "europe-west1"): 0.11,
    ("asia-west1", "europe-west2"): 0.11,
    ("asia-west1", "europe-west3"): 0.11,
    ("asia-west1", "europe-north1"): 0.11,
    ("asia-west1", "europe-south1"): 0.11,
    ("asia-east1", "asia-northeast1"): 0.08,
    ("asia-east1", "asia-southeast1"): 0.08,
    ("asia-east1", "asia-west1"): 0.11,
    ("asia-northeast1", "asia-east1"): 0.08,
    ("asia-northeast1", "asia-southeast1"): 0.08,
    ("asia-northeast1", "asia-west1"): 0.11,
    ("asia-southeast1", "asia-east1"): 0.08,
    ("asia-southeast1", "asia-northeast1"): 0.08,
    ("asia-southeast1", "asia-west1"): 0.11,
    ("asia-west1", "asia-east1"): 0.11,
    ("asia-west1", "asia-northeast1"): 0.11,
    ("asia-west1", "asia-southeast1"): 0.11,
    ("asia-east1", "asia-southeast2"): 0.1,
    ("asia-northeast1", "asia-southeast2"): 0.1,
    ("asia-southeast1", "asia-southeast2"): 0.1,
    ("asia-west1", "asia-southeast2"): 0.11,
    ("asia-east1", "australia-southeast1"): 0.1,
    ("asia-northeast1", "australia-southeast1"): 0.1,
    ("asia-southeast1", "australia-southeast1"): 0.1,
    ("asia-west1", "australia-southeast1"): 0.11,
    ("asia-east1", "southamerica-east1"): 0.14,
    ("asia-northeast1", "southamerica-east1"): 0.14,
    ("asia-southeast1", "southamerica-east1"): 0.14,
    ("asia-west1", "southamerica-east1"): 0.14,
    ("asia-east1", "africa-west1"): 0.11,
    ("asia-northeast1", "africa-west1"): 0.11,
    ("asia-southeast1", "africa-west1"): 0.11,
    ("asia-west1", "africa-west1"): 0.11,
    ("asia-southeast2", "northamerica-northeast1"): 0.1,
    ("asia-southeast2", "us-east1"): 0.1,
    ("asia-southeast2", "us-west1"): 0.1,
    ("asia-southeast2", "us-west2"): 0.1,
    ("asia-southeast2", "europe-west1"): 0.1,
    ("asia-southeast2", "europe-west2"): 0.1,
    ("asia-southeast2", "europe-west3"): 0.1,
    ("asia-southeast2", "europe-north1"): 0.1,
    ("asia-southeast2", "europe-south1"): 0.1,
    ("asia-southeast2", "asia-east1"): 0.1,
    ("asia-southeast2", "asia-northeast1"): 0.1,
    ("asia-southeast2", "asia-southeast1"): 0.1,
    ("asia-southeast2", "asia-west1"): 0.11,
    ("asia-southeast2", "australia-southeast1"): 0.1,
    ("asia-southeast2", "southamerica-east1"): 0.14,
    ("asia-southeast2", "africa-west1"): 0.14,
    ("australia-southeast1", "northamerica-northeast1"): 0.1,
    ("australia-southeast1", "us-east1"): 0.1,
    ("australia-southeast1", "us-west1"): 0.1,
    ("australia-southeast1", "us-west2"): 0.1,
    ("australia-southeast1", "europe-west1"): 0.1,
    ("australia-southeast1", "europe-west2"): 0.1,
    ("australia-southeast1", "europe-west3"): 0.1,
    ("australia-southeast1", "europe-north1"): 0.1,
    ("australia-southeast1", "europe-south1"): 0.1,
    ("australia-southeast1", "asia-east1"): 0.1,
    ("australia-southeast1", "asia-northeast1"): 0.1,
    ("australia-southeast1", "asia-southeast1"): 0.1,
    ("australia-southeast1", "asia-west1"): 0.11,
    ("australia-southeast1", "asia-southeast2"): 0.1,
    ("australia-southeast1", "southamerica-east1"): 0.14,
    ("australia-southeast1", "africa-west1"): 0.14,
    ("southamerica-east1", "northamerica-northeast1"): 0.14,
    ("southamerica-east1", "us-east1"): 0.14,
    ("southamerica-east1", "us-west1"): 0.14,
    ("southamerica-east1", "us-west2"): 0.14,
    ("southamerica-east1", "europe-west1"): 0.14,
    ("southamerica-east1", "europe-west2"): 0.14,
    ("southamerica-east1", "europe-west3"): 0.14,
    ("southamerica-east1", "europe-north1"): 0.14,
    ("southamerica-east1", "europe-south1"): 0.14,
    ("southamerica-east1", "asia-east1"): 0.14,
    ("southamerica-east1", "asia-northeast1"): 0.14,
    ("southamerica-east1", "asia-southeast1"): 0.14,
    ("southamerica-east1", "asia-west1"): 0.14,
    ("southamerica-east1", "asia-southeast2"): 0.14,
    ("southamerica-east1", "australia-southeast1"): 0.14,
    ("southamerica-east1", "africa-west1"): 0.14,
    ("africa-west1", "northamerica-northeast1"): 0.11,
    ("africa-west1", "us-east1"): 0.11,
    ("africa-west1", "us-west1"): 0.11,
    ("africa-west1", "us-west2"): 0.11,
    ("africa-west1", "europe-west1"): 0.11,
    ("africa-west1", "europe-west2"): 0.11,
    ("africa-west1", "europe-west3"): 0.11,
    ("africa-west1", "europe-north1"): 0.11,
    ("africa-west1", "europe-south1"): 0.11,
    ("africa-west1", "asia-east1"): 0.11,
    ("africa-west1", "asia-northeast1"): 0.11,
    ("africa-west1", "asia-southeast1"): 0.11,
    ("africa-west1", "asia-west1"): 0.11,
    ("africa-west1", "asia-southeast2"): 0.14,
    ("africa-west1", "australia-southeast1"): 0.14,
    ("africa-west1", "southamerica-east1"): 0.14,
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


network = create_graph(nodes, calculate_cost=calculate_cost)

if __name__ == "__main__":
    display_triangle_inequality_satisfaction(network)
