from fastapi import APIRouter, Query
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
from playwright.sync_api import sync_playwright

router = APIRouter()

def fetch_html_with_playwright(url: str) -> str:
    """Fetch rendered HTML using Playwright (executes JavaScript)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        content = page.content()
        browser.close()
    return content

@router.get("/onpage")
def onpage_analysis(url: str, keyword: str = Query(None, description="Optional keyword for SEO analysis")):
    try:
        # --- Fetch fully rendered HTML ---
        html = fetch_html_with_playwright(url)
        soup = BeautifulSoup(html, "html.parser")

        # Title
        title = soup.title.string.strip() if soup.title else None
        title_status = None
        if title:
            if len(title) < 30:
                title_status = "Too short"
            elif len(title) > 60:
                title_status = "Too long"
            else:
                title_status = "Good length"

        # Meta description
        meta_desc_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
        meta_description = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else None

        # Headings (deduplicate for cleanliness)
        headings = {
            "h1": list(dict.fromkeys([h.get_text(strip=True) for h in soup.find_all("h1")])),
            "h2": list(dict.fromkeys([h.get_text(strip=True) for h in soup.find_all("h2")])),
            "h3": list(dict.fromkeys([h.get_text(strip=True) for h in soup.find_all("h3")]))
        }

        # Canonical
        canonical_tag = soup.find("link", attrs={"rel": "canonical"})
        canonical = canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else None

        # Robots meta
        robots_meta_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "robots"})
        robots_meta = robots_meta_tag["content"] if robots_meta_tag and robots_meta_tag.get("content") else "index, follow"

        # Image audit (works now with JS-rendered HTML)
        all_imgs = soup.find_all("img")
        missing_alt = [img.get("src") for img in all_imgs if not img.get("alt") and img.get("src")]
        alt_stats = {
            "total_images": len(all_imgs),
            "missing_alt_count": len(missing_alt),
            "missing_alt_percent": round((len(missing_alt) / len(all_imgs) * 100), 2) if all_imgs else 0
        }

        # Word count
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        body_text = soup.get_text(" ", strip=True)
        words = re.findall(r"\b\w+\b", body_text.lower())
        word_count = len(words)

        # Internal vs external links
        domain = urlparse(url).netloc
        internal_links, external_links = [], []
        for link in soup.find_all("a", href=True):
            href = urljoin(url, link["href"].strip())
            if domain in urlparse(href).netloc:
                internal_links.append(href)
            else:
                external_links.append(href)

        # Keyword analysis
        keyword_analysis = {}
        if keyword:
            # Detailed analysis for provided keyword
            kw = keyword.lower()
            keyword_analysis = {
                "keyword": keyword,
                "in_title": bool(title and kw in title.lower()),
                "in_meta_desc": bool(meta_description and kw in meta_description.lower()),
                "in_headings": any(kw in h.lower() for h in headings["h1"] + headings["h2"] + headings["h3"]),
                "count_in_body": body_text.lower().count(kw),
                "density_percent": round((body_text.lower().count(kw) / word_count * 100), 2) if word_count else 0
            }
        else:
            # Return top 10 frequent terms if no keyword provided
            stopwords = {"the","and","or","for","of","a","an","to","in","on","at","by","with","is","are","was","were"}
            freq = {}
            for w in words:
                if w not in stopwords and len(w) > 2:
                    freq[w] = freq.get(w, 0) + 1
            common_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]

            keyword_analysis = {
                "top_terms": [
                    {
                        "term": term,
                        "count": count,
                        "in_title": bool(title and term in title.lower()),
                        "in_meta_desc": bool(meta_description and term in meta_description.lower()),
                        "in_headings": any(term in h.lower() for h in headings["h1"] + headings["h2"] + headings["h3"])
                    }
                    for term, count in common_terms
                ]
            }

        return {
            "onpage": {
                "url": url,
                "title": title,
                "title_status": title_status,
                "meta_description": meta_description,
                "headings": headings,
                "canonical": canonical,
                "robots_meta": robots_meta,
                "alt_audit": alt_stats,
                "word_count": word_count,
                "internal_links": len(internal_links),
                "external_links": len(external_links),
                "keyword_analysis": keyword_analysis
            }
        }

    except Exception as e:
        return {"error": str(e)}
