import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import gzip

# ✅ FIX: Add headers to bypass caching proxies
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

def fetch_robots_txt(url: str) -> dict:
    """
    Fetches and parses the robots.txt file for a given URL.
    """
    robots_url = urljoin(url, "/robots.txt")
    try:
        response = requests.get(robots_url, timeout=10, headers=HEADERS)
        if response.status_code != 200:
            return {"allows": True, "disallows": []}
        
        disallows = set()  # Use a set to auto-handle duplicates
        allows_all = True
        for line in response.text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.lower().startswith("disallow:"):
                allows_all = False
                disallows.add(line.split(":", 1)[1].strip())
        
        return {"allows": allows_all, "disallows": list(disallows)}
    except Exception:
        return {"allows": True, "disallows": []}


def fetch_sitemap(url: str) -> dict:
    """
    Finds sitemap URLs from robots.txt, falls back to a default, and fetches page URLs.
    """
    robots_url = urljoin(url, "/robots.txt")
    sitemap_locations = []
    sitemap_urls = []

    # Step 1: Parse robots.txt to find all sitemap entries
    try:
        response = requests.get(robots_url, timeout=10, headers=HEADERS)
        if response.ok:
            for line in response.text.splitlines():
                clean_line = line.strip().lower()
                if clean_line.startswith("sitemap:"):
                    sitemap_path = line.split(":", 1)[1].strip()
                    full_sitemap_url = urljoin(url, sitemap_path)
                    sitemap_locations.append(full_sitemap_url)
    except Exception:
        pass

    # Step 2: If no sitemaps were found, use the common default
    if not sitemap_locations:
        sitemap_locations.append(urljoin(url, "/sitemap.xml"))

    # Step 3: Process each full sitemap URL we found
    for sm_url in sitemap_locations:
        try:
            sub_resp = requests.get(sm_url, timeout=10, headers=HEADERS)
            if not sub_resp.ok:
                continue

            sub_content = sub_resp.content
            if sm_url.endswith(".gz"):
                sub_content = gzip.decompress(sub_content)

            try:
                sub_root = ET.fromstring(sub_content)
                if sub_root.tag.endswith("sitemapindex"):
                    for sitemap in sub_root.findall(".//{*}sitemap/{*}loc"):
                        nested_sm_url = sitemap.text.strip()
                        try:
                            nested_resp = requests.get(nested_sm_url, timeout=10, headers=HEADERS)
                            if nested_resp.ok:
                                nested_content = nested_resp.content
                                if nested_sm_url.endswith(".gz"):
                                    nested_content = gzip.decompress(nested_content)
                                nested_root = ET.fromstring(nested_content)
                                for loc in nested_root.findall(".//{*}url/{*}loc"):
                                    sitemap_urls.append(loc.text.strip())
                                    if len(sitemap_urls) >= 50: break
                        except Exception: continue
                        if len(sitemap_urls) >= 50: break

                elif sub_root.tag.endswith("urlset"):
                    for loc in sub_root.findall(".//{*}url/{*}loc"):
                        sitemap_urls.append(loc.text.strip())
                        if len(sitemap_urls) >= 50: break
            except ET.ParseError: continue
        except Exception: continue
        if len(sitemap_urls) >= 50: break

    return {
        "sitemaps_checked": sitemap_locations,
        "sitemap_urls": sitemap_urls[:50]
    }


def crawlability_audit(url: str) -> dict:
    """
    Performs a crawlability audit by checking robots.txt and sitemaps.
    """
    return {
        "crawlability": {
            "robots_txt": fetch_robots_txt(url),
            "sitemap_info": fetch_sitemap(url),
            "canonical_consistency": "TODO - will compare with Person A’s canonical"
        }
    }


if __name__ == "__main__":
    test_url = "https://en.wikipedia.org"
    print(crawlability_audit(test_url))