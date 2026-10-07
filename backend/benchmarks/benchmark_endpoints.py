"""
Mesaure system performance(latency) of key endpoints:
- /api/pois
- /api/pois/{slug}
- /api/itinerary/generate
- /api/ai/converstions/{conversation_id}/messages

Run file locally:
    cd backend
    python -m benchmarks.benchmark_endpoints
"""

import getpass
import os
import statistics
import time

import requests

# BASE_URL = "https://api.offpeak.live/api"
BASE_URL = os.environ.get("OFFPEAK_API", "http://127.0.0.1:8000/api")

AI_PAYLOAD = {
    "prompt": "Plan a trip to Manhattan focusing on museums and landmarks"
    }

def benchmark_endpoint(url, title, runs, payload=None):
    times = []
    counts = []
    
    # warm up (in case of cold start)
    warmup_start = time.perf_counter()

    if payload is not None:
        response = requests.post(url, json=payload)
    else:
        response = requests.get(url)
    
    response.raise_for_status()

    if "X-Query-Count" not in response.headers:
        raise SystemExit(
            f"X-Query-Count header missing from {response.url}. Set ENABLE_QUERY_COUNTER=true in backend/.env and restart uvicorn.")

    warmup_end = time.perf_counter()

    initial_request_time = (warmup_end - warmup_start) * 1000

    # main benchmark
    for _ in range(runs):
        start = time.perf_counter()

        if payload is not None:
            response = requests.post(url, json=payload)
        else:
            response = requests.get(url)

        response.raise_for_status()

        end = time.perf_counter()

        times.append((end - start) * 1000)

        # SQL request count
        counts.append(int(response.headers["X-Query-Count"]))

    
    # time metric calculation
    median_time = statistics.median(times)
    p95 = statistics.quantiles(times, n=100)[94]
    median_count = statistics.median(counts)
   
   # show results
    print("-----------------------")
    print(f"Title: {title}")
    print(f"Initial request latency: {initial_request_time:.2f} ms")
    print(f"Median latency: {median_time:.2f} ms")
    print(f"P95 latency: {p95:.2f} ms")
    print(f"Median count: {median_count:.2f} times")
    
# test /pois, /pois/{slug} and /itinerary/generate endpoints
benchmark_endpoint(
    url=f"{BASE_URL}/pois/", 
    title="POIs List",
    runs=100
    )

benchmark_endpoint(
    url=f"{BASE_URL}/pois/central-park", 
    title="POI Detail",
    runs=100
    )
print("======= Itinerary Generation: POI = 3 ==========")
# POI = 3
benchmark_endpoint(
    url=f"{BASE_URL}/itinerary/generate", 
    title="Itinerary Generation",
    runs=100,
    payload={
        "trip_name": "mock_itinerary",
        "trip_dates": ["2026-08-03","2026-08-05"],
        "pois": [
            "central-park", "times-square", "the-high-line"
            ],
        "accessibility": []
        }
    )
# POI = 5
print("======= Itinerary Generation: POI = 5 ==========")
benchmark_endpoint(
    url=f"{BASE_URL}/itinerary/generate", 
    title="Itinerary Generation",
    runs=100,
    payload={
        "trip_name": "mock_itinerary",
        "trip_dates": ["2026-08-03","2026-08-05"],
        "pois": [
            "central-park", "times-square", "the-high-line", 
            "grand-central-terminal", "empire-state-building"
            ],
        "accessibility": []
        }
    )
# POI = 9
print("======= Itinerary Generation: POI = 9 ==========")
benchmark_endpoint(
    url=f"{BASE_URL}/itinerary/generate", 
    title="Itinerary Generation",
    runs=100,
    payload={
        "trip_name": "mock_itinerary",
        "trip_dates": ["2026-08-03","2026-08-05"],
        "pois": [
            "central-park", "times-square", "the-high-line", 
            "grand-central-terminal", "empire-state-building", "bryant-park", 
            "rockefeller-center", "little-island", "pier-17"
            ],
        "accessibility": []
        }
    )

print("=============== AI calls =======================")

# test /ai/converstions/{id}/messages endpoint
# login (with Offpeak credentials)
session = requests.Session()

email = input("Email: ")
password = getpass.getpass("Password: ")

response = session.post(
     
    f"{BASE_URL}/auth/mobile/login",
    json={
        "email": email,
        "password": password
    }
)
response.raise_for_status()
access_token = response.json()["access_token"]

# calculate warmup time for ai planner
session.headers["Authorization"] = f"Bearer {access_token}"
response = session.post(
        f"{BASE_URL}/ai/conversations",
        json={}
    )
response.raise_for_status()
conversation_id = response.json()["conversation_id"]

start = time.perf_counter()
response = session.post(
    f"{BASE_URL}/ai/converstions/{conversation_id}/messages",
    json=AI_PAYLOAD
)
response.raise_for_status()
end = time.perf_counter()
initial_request_time = (end - start) * 1000



# hit ai endpoint 20 times
ai_times = []
counts = []
for _ in range(5):
    
    response = session.post(
        f"{BASE_URL}/ai/conversations",
        json={}
    )
    response.raise_for_status()


    conversation_id = response.json()["conversation_id"]

    start = time.perf_counter()
    response = session.post(
        f"{BASE_URL}/ai/converstions/{conversation_id}/messages",
        json=AI_PAYLOAD
        )
    response.raise_for_status()
    end = time.perf_counter()

    if "X-Query-Count" not in response.headers:
                    raise SystemExit(
                        f"X-Query-Count header missing from {response.url}. Set ENABLE_QUERY_COUNTER=true in backend/.env and restart uvicorn.")
    
    ai_times.append((end - start) * 1000)
    counts.append(int(response.headers["X-Query-Count"]))
    print("********AI call completed**********")

# time metric calculation
median_time = statistics.median(ai_times)
sorted_times = sorted(ai_times)
p95 = sorted_times[int(0.95 * len(sorted_times)) - 1]
median_count = statistics.median(counts) 

# show ai endpoint results
print("-----------------------")
print("Title: AI Planner")
print(f"Initial request latency: {initial_request_time:.2f} ms")
print(f"Median latency: {median_time:.2f} ms")
print(f"P95 latency: {p95:.2f} ms")
print(f"Median SQL request count: {median_count} time(s)")





