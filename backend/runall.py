import requests

BASE = "http://127.0.0.1:8000"
URL = "https://apple.com"

print("---- PERSON A: Onpage ----")
print(requests.get(f"{BASE}/onpage", params={"url": URL}).json())

print("\n---- PERSON C: Crawlability ----")
print(requests.get(f"{BASE}/crawl", params={"url": URL}).json())

print("\n---- PERSON B: Performance ----")
print(requests.get(f"{BASE}/performance", params={"url": URL}).json())