import time
import requests

BASE_URL = "http://127.0.0.1:8000"


track_human_readable_name = "Gajdos Összes Rövidítve"
track_namespace = "vod"
track_name = "gajdos-osszes-roviditve"
publisher = "us-west1"
delay_budget = 1000

subscribers = ["us-west2", "us-east1", "europe-south1", "europe-west1", "europe-west2", "europe-west3", "southamerica-east1", "asia-west1", "asia-east1"]


response = requests.post(f"{BASE_URL}/tracks/{track_namespace}/{track_name}", json={
    "name": track_human_readable_name,
    "publisher": publisher,
    "delay_budget": delay_budget
})
assert response.status_code == 201

for subscriber in subscribers:
    start = time.time()
    
    response = requests.post(f"{BASE_URL}/tracks/{track_namespace}/{track_name}/subscribe?optimizer_type=minimum_spanning_tree", json=subscriber)
    assert response.status_code == 200
    
    end = time.time()
    rtt = (end - start) * 1000
    
    print(f"[RTT = {rtt} ms]: {subscriber} should get from {response.json()}")
