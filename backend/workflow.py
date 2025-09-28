import os, json, subprocess, requests, pathlib, time
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
BASE = "http://127.0.0.1:8000"
GAMMA_API_KEY = os.getenv("GAMMA_API_KEY")

def fetch_all(url: str):
    """Fetch results from all three local API endpoints."""
    data = {}
    try:
        data["onpage"] = requests.get(f"{BASE}/onpage", params={"url": url}, timeout=90).json()
        data["crawlability"] = requests.get(f"{BASE}/crawl", params={"url": url}, timeout=30).json()
        data["performance"] = requests.get(f"{BASE}/performance", params={"url": url}, timeout=180).json()
    except Exception as e:
        print(f"⚠️ An error occurred during data fetching: {e}")
        return None
    return data

def run_ollama(summary: dict) -> str:
    """Send combined JSON to Ollama and return raw output."""
    prompt = f"""
# ROLE & GOAL
You are an expert SEO analyst. Your only task is to generate a structured report based on the provided JSON data. You must follow all formatting rules precisely.

# CRITICAL RULES
- YOU MUST include the `### SLIDES START` marker at the beginning of the slides.
- YOU MUST include the `### SLIDES END` marker at the very end of the slides.
- Failure to include both markers is not an option. Double-check your output.

---
### SLIDES START
## Slide 1: Executive Summary & Overall SEO Health
- High-level overview of the site's SEO posture.
- Mention overall performance scores (mobile/desktop).
- Summarize key findings from crawlability and on-page analysis.
- State the site's main strengths and biggest growth opportunity.
*Key Takeaway*: A single sentence summarizing the site's current state and potential.

## Slide 2: Core Web Vitals & Performance (Mobile-First)
- Focus on **mobile** performance metrics.
- Cite specific mobile scores (Performance, Accessibility, SEO).
- Explain what a low score means for user experience and rankings.
- Mention Core Web Vitals (LCP, CLS) and suggest technical improvements.
*Key Takeaway*: Summarize the urgency and impact of mobile performance.

## Slide 3: Desktop User Experience & Performance
- Focus on **desktop** performance metrics.
- Compare desktop scores directly to mobile scores.
- Discuss any significant differences and why they might exist.
- Relate desktop performance to conversion rates.
*Key Takeaway*: State whether the desktop experience is a strength or a liability.

## Slide 4: Crawlability & Technical SEO
- State if the site is crawlable.
- Explain the role of `robots.txt` and list any important blocked URLs.
- Analyze the impact of these blocks (are they good or bad?).
- Recommend a review of the `robots.txt` file.
*Key Takeaway*: Conclude if the site has a solid technical foundation for search engines.

## Slide 5: On-Page Content & Meta Tags
- State the total `word_count` and discuss if it's appropriate.
- List primary meta tags found (`title`, `description`).
- Evaluate the quality of the meta title and description for click-through rates.
- Suggest specific improvements for the meta tags.
*Key Takeaway*: State if the on-page content is well-structured and optimized.

## Slide 6: Keyword Landscape
- List the top 3-5 keywords and their frequency.
- Analyze if these keywords align with the page's topic.
- Recommend strategies to better target primary keywords.
- Discuss incorporating long-tail keyword variations.
*Key Takeaway*: Summarize how well the page's content matches user search intent.

## Slide 7: Link Profile Analysis
- State the number of `internal_links` and `external_links`.
- Explain the role of internal links in distributing authority.
- Discuss the purpose and quality of external links.
- Recommend checking for broken links.
*Key Takeaway*: Conclude on the health of the page's linking strategy.

## Slide 8: Priority Recommendations & Next Steps
- Synthesize the action points from previous slides into a prioritized list.
- Priority 1 (High Impact): The most critical issue (e.g., "Fix mobile performance").
- Priority 2 (Medium Impact): Next most important (e.g., "Rewrite meta tags").
- Conclude with a forward-looking statement about growth potential.
*Key Takeaway*: A final, encouraging call to action.
### SLIDES END
---
### JSON INPUT
{json.dumps(summary, indent=2)}
"""
    result = subprocess.run(["ollama", "run", "llama3"], input=prompt.encode("utf-8"), capture_output=True)
    return result.stdout.decode("utf-8")

def parse_and_upload(raw_output: str):
    """Parses LLM output, starts Gamma generation, and polls for the result. Returns the final URL."""
    slides = ""
    start_marker, end_marker = "### SLIDES START", "### SLIDES END"
    if start_marker in raw_output:
        content_after_start = raw_output.split(start_marker, 1)[1]
        if end_marker in content_after_start:
            slides = content_after_start.split(end_marker, 1)[0].strip()
        else:
            slides = content_after_start.strip()

    if not (GAMMA_API_KEY and slides):
        return None

    try:
        start_endpoint = "https://public-api.gamma.app/v0.2/generations"
        headers = {"X-API-KEY": GAMMA_API_KEY, "Content-Type": "application/json"}
        payload = {"inputText": slides, "textMode": "preserve", "cardSplit": "inputTextBreaks"}
        resp = requests.post(start_endpoint, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        generation_id = resp.json().get("generationId")
        if not generation_id: return None

        status_endpoint = f"https://public-api.gamma.app/v0.2/generations/{generation_id}"
        for _ in range(20):
            time.sleep(5)
            status_resp = requests.get(status_endpoint, headers=headers, timeout=30)
            status_resp.raise_for_status()
            status_data = status_resp.json()
            status = status_data.get("status")
            if status == "completed":
                return status_data.get("gammaUrl")
            if status == "failed":
                return None
        return None
    except Exception as e:
        print(f"⚠️ An error occurred during Gamma upload: {e}")
        return None

def run_full_workflow(job_id: str, url: str, statuses: dict):
    """Orchestrates the entire process and updates the job status dictionary."""
    print(f"--- [Job {job_id}] Starting for: {url} ---")
    statuses[job_id] = {"status": "fetching_data", "result": None}
    summary = fetch_all(url)
    if not summary:
        statuses[job_id] = {"status": "failed", "result": "Failed to fetch initial SEO data."}
        return

    print(f"--- [Job {job_id}] Generating text with Ollama... ---")
    statuses[job_id] = {"status": "generating_text", "result": None}
    raw_output = run_ollama(summary)

    print(f"--- [Job {job_id}] Creating presentation with Gamma... ---")
    statuses[job_id] = {"status": "creating_presentation", "result": None}
    final_url = parse_and_upload(raw_output)
    
    if final_url:
        statuses[job_id] = {"status": "complete", "result": final_url}
        print(f"--- [Job {job_id}] Successfully finished. ---")
    else:
        statuses[job_id] = {"status": "failed", "result": "Failed to create the Gamma presentation."}
        print(f"--- [Job {job_id}] Failed during Gamma presentation creation. ---")