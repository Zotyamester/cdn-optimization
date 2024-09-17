import random
import sys
import time
import requests

BASE_URL = "http://127.0.0.1:800%d" % int(sys.argv[1] if len(sys.argv) > 1 else '0')

network = requests.get(f"{BASE_URL}/network").json()
nodes = list(map(lambda obj: obj["name"], network["nodes"]))

random.seed(69)
peers = random.sample(nodes, k=int(len(nodes) * 0.55))

track_namespace = "live"
delay_budget = 1000
publisher, *subscribers = peers

optimizer_type = "multicast_heuristic"
reduce_network = False

response = requests.post(f"{BASE_URL}/tracks/{track_namespace}", json={
    "publisher": publisher,
    "delay_budget": delay_budget
})
assert response.status_code == 201

for subscriber in subscribers:
    start = time.time()
    
    response = requests.post(f"{BASE_URL}/tracks/{track_namespace}/subscription/{subscriber}?optimizer_type={optimizer_type}&reduce_network={reduce_network}")
    assert response.status_code == 200
    
    end = time.time()
    rtt = (end - start) * 1000
    
    print(f"[RTT = {rtt} ms]: {subscriber} should get from {response.json()}")
