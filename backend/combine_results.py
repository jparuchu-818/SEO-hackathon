# backend/combine_results.py
import requests

BASE = "http://127.0.0.1:8000"  # FastAPI must be running
TIMEOUT = 60

def combine_results(url: str) -> dict:
    """Fetch onpage, crawlability, and performance results for a URL and merge them."""
    results = {"url": url}

    try:
        onpage = requests.get(f"{BASE}/onpage", params={"url": url}, timeout=TIMEOUT).json()
        results["onpage"] = onpage.get("onpage", onpage)
    except Exception as e:
        results["onpage"] = {"error": str(e)}

    try:
        crawl = requests.get(f"{BASE}/crawl", params={"url": url}, timeout=TIMEOUT).json()
        results["crawlability"] = crawl.get("crawlability", crawl)
    except Exception as e:
        results["crawlability"] = {"error": str(e)}

    try:
        perf = requests.get(f"{BASE}/performance", params={"url": url}, timeout=TIMEOUT).json()
        results["performance"] = perf.get("pagespeed", perf)
    except Exception as e:
        results["performance"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    test_url = "https://apple.com"
    combined = combine_results(test_url)
    import json
    print(json.dumps(combined, indent=2))
