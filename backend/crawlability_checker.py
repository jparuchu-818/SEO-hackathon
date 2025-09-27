import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import gzip

def fetch_robots_txt(url: str, target_agent: str = "*") -> dict:
    robots_url = urljoin(url, "/robots.txt")
    disallows = []
    allows_all = True
    current_agent = None
    relevant = False

    try:
        response = requests.get(robots_url, timeout=10)
        if response.status_code != 200:
            return {"allows": True, "disallows": []}

        for line in response.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip().lower()
                # Check if this block applies to the target agent
                relevant = (current_agent == target_agent or current_agent == "*")

            elif line.lower().startswith("disallow:") and relevant:
                allows_all = False
                path = line.split(":", 1)[1].strip()
                disallows.append(path if path else "/")

        return {"allows": allows_all, "disallows": disallows}
    except Exception:
        return {"allows": True, "disallows": []}


def fetch_sitemap(url: str, limit: int = 10) -> dict:
    robots_url = urljoin(url, "/robots.txt")
    sitemap_locations = []
    sitemap_urls = []

    # Step 1: Look inside robots.txt
    try:
        response = requests.get(robots_url, timeout=10)
        if response.ok:
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sm_url = line.split(":", 1)[1].strip()
                    full_sitemap_url = urljoin(url, sm_url)
                    sitemap_locations.append(full_sitemap_url)
    except Exception:
        pass

    # Step 2: Fallback if robots.txt has no sitemap
    if not sitemap_locations:
        sitemap_locations.append(urljoin(url, "/sitemap.xml"))

    # Step 3: Parse sitemaps
    for sm_url in sitemap_locations:
        try:
            resp = requests.get(sm_url, timeout=10)
            if not resp.ok:
                continue
            content = resp.content
            if sm_url.endswith(".gz"):
                content = gzip.decompress(content)

            root = ET.fromstring(content)

            # Sitemap Index → nested sitemaps
            if root.tag.endswith("sitemapindex"):
                for sitemap in root.findall(".//{*}sitemap/{*}loc"):
                    nested_url = sitemap.text.strip()
                    try:
                        nested_resp = requests.get(nested_url, timeout=10)
                        if nested_resp.ok:
                            nested_content = nested_resp.content
                            if nested_url.endswith(".gz"):
                                nested_content = gzip.decompress(nested_content)
                            nested_root = ET.fromstring(nested_content)
                            for loc in nested_root.findall(".//{*}url/{*}loc"):
                                sitemap_urls.append(loc.text.strip())
                                if len(sitemap_urls) >= limit:
                                    break
                    except Exception:
                        continue
                    if len(sitemap_urls) >= limit:
                        break

            # Regular sitemap
            elif root.tag.endswith("urlset"):
                for loc in root.findall(".//{*}url/{*}loc"):
                    sitemap_urls.append(loc.text.strip())
                    if len(sitemap_urls) >= limit:
                        break
        except Exception:
            continue
        if len(sitemap_urls) >= limit:
            break

    return {
        "sitemaps_checked": sitemap_locations,
        "sitemap_urls_sample": sitemap_urls[:limit],
        "total_urls": len(sitemap_urls)
    }


def crawlability_audit(url: str, onpage_data: dict = None) -> dict:
    robots_data = fetch_robots_txt(url)
    sitemap_data = fetch_sitemap(url)

    # Default indexing signals
    indexing_signals = {
        "robots_meta": None,
        "canonical": None,
        "canonical_consistency": None,
    }

    if onpage_data:  # Integrate Person A’s results if available
        indexing_signals["robots_meta"] = onpage_data.get("robots_meta")
        indexing_signals["canonical"] = onpage_data.get("canonical")

        # Compare sitemap vs canonical
        if sitemap_data["sitemap_urls_sample"] and indexing_signals["canonical"]:
            first_sitemap_url = sitemap_data["sitemap_urls_sample"][0]
            if indexing_signals["canonical"].rstrip("/") == first_sitemap_url.rstrip("/"):
                indexing_signals["canonical_consistency"] = "Matches"
            else:
                indexing_signals["canonical_consistency"] = "Mismatch"
        else:
            indexing_signals["canonical_consistency"] = "Not enough data"

    # Create summary
    summary_notes = []
    status = "Fully Indexable"

    if not robots_data["allows"]:
        status = "Issues Found"
        summary_notes.append("Blocked by robots.txt")

    if not sitemap_data["sitemap_urls_sample"]:
        status = "Issues Found"
        if sitemap_data["sitemaps_checked"]:
            summary_notes.append("Sitemap found but empty")
        else:
            summary_notes.append("No sitemap found")

    if indexing_signals["canonical_consistency"] == "Mismatch":
        status = "Issues Found"
        summary_notes.append("Canonical mismatch")

    if indexing_signals["robots_meta"] and "noindex" in indexing_signals["robots_meta"].lower():
        status = "Issues Found"
        summary_notes.append("Page-level noindex found")

    return {
        "crawlability": {
            "robots_txt": robots_data,
            "sitemap_info": sitemap_data,
            "indexing_signals": indexing_signals,
            "summary": {
                "status": status,
                "notes": summary_notes if summary_notes else ["All clear"]
            }
        }
    }


if __name__ == "__main__":
    test_url = "https://yoast.com"
    print(crawlability_audit(test_url))
