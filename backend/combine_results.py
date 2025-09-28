# backend/combine_results.py
import os, json, subprocess, requests, pathlib
import time

# --- CONFIGURATION ---
BASE = "http://127.0.0.1:8000"
URL = "https://www.dosystemsinc.com/.com"
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 🔑 PASTE YOUR API KEY HERE
# This is the only secret you need.
from dotenv import load_dotenv
load_dotenv()
GAMMA_API_KEY = os.getenv("GAMMA_API_KEY")

if not GAMMA_API_KEY:
    raise ValueError("GAMMA_API_KEY not found. Make sure you have a .env file in the root directory.")


def fetch_all(url: str):
    """Fetch results from all three endpoints"""
    data = {}
    try:
        print(f"Fetching /onpage for {url}...")
        data["onpage"] = requests.get(f"{BASE}/onpage", params={"url": url}).json()
        print(f"Fetching /crawl for {url}...")
        data["crawlability"] = requests.get(f"{BASE}/crawl", params={"url": url}).json()
        print(f"Fetching /performance for {url}...")
        data["performance"] = requests.get(f"{BASE}/performance", params={"url": url}).json()
        print("✅ All data fetched successfully.")
    except requests.exceptions.ConnectionError:
        print("⚠️ Connection Error: Could not connect to the server.")
        print("   Please make sure your FastAPI server (main.py) is running in another terminal.")
    except Exception as e:
        print(f"⚠️ An error occurred during fetching: {e}")
    return data

def run_ollama(summary: dict) -> str:
    """Send combined JSON to Ollama and return raw output"""
    # This prompt is working well, so we'll keep it.
    prompt = f"""
# ROLE & GOAL
You are an expert SEO analyst. Your only task is to generate a structured report based on the provided JSON data. You must follow all formatting rules precisely.

# CRITICAL RULES
- YOU MUST include the `### SLIDES START` marker at the beginning of the slides.
- YOU MUST include the `### SLIDES END` marker at the very end of the slides.
- YOU MUST include the `### METRICS START` and `### METRICS END` markers around the JSON block.
- Failure to include all four markers is not an option. Double-check your output.

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
- State if the site is crawlable (`is_crawlable`).
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
### METRICS START
{{
  "performance": {{
    "mobile": {{ "performance": int, "seo": int, "accessibility": int, "best_practices": int }},
    "desktop": {{ "performance": int, "seo": int, "accessibility": int, "best_practices": int }}
  }},
  "links": {{ "internal": int, "external": int }},
  "keywords": [ {{ "term": str, "count": int }} ],
  "word_count": int
}}
### METRICS END

---
### JSON INPUT
{json.dumps(summary, indent=2)}
"""
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt.encode("utf-8"),
        capture_output=True,
    )
    return result.stdout.decode("utf-8")

def parse_and_upload(raw_output: str):
    """Parses the LLM output, starts generation, and polls for the result."""
    slides, metrics = "", "{}"
    
    start_marker = "### SLIDES START"
    end_marker = "### SLIDES END"
    if start_marker in raw_output:
        content_after_start = raw_output.split(start_marker, 1)[1]
        if end_marker in content_after_start:
            slides = content_after_start.split(end_marker, 1)[0].strip()
        else:
            print("⚠️ SLIDES END marker not found. Parsing all content after start marker as a fallback.")
            slides = content_after_start.strip()

    num_slides = slides.count("## Slide")
    print(f"✅ Parsed: {num_slides} slides.")

    if GAMMA_API_KEY and slides:
        try:
            # --- STEP 1: START THE GENERATION ---
            print("🚀 Submitting generation request to Gamma...")
            start_endpoint = "https://public-api.gamma.app/v0.2/generations"
            headers = { "X-API-KEY": GAMMA_API_KEY, "Content-Type": "application/json" }
            payload = { "inputText": slides, "textMode": "preserve", "cardSplit": "inputTextBreaks" }
            resp = requests.post(start_endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            start_data = resp.json()
            generation_id = start_data.get("generationId")
            if not generation_id:
                print("⚠️ Failed to start generation. Response:", start_data)
                return
            print(f"✅ Generation started with ID: {generation_id}")

            # --- STEP 2: POLL FOR THE RESULT ---
            print("⏳ Waiting for presentation to be generated... (this may take up to 100 seconds)")
            status_endpoint = f"https://public-api.gamma.app/v0.2/generations/{generation_id}"
            
            for i in range(20):
                time.sleep(5) 
                status_resp = requests.get(status_endpoint, headers=headers)
                status_resp.raise_for_status()
                status_data = status_resp.json()
                status = status_data.get("status")
                
                print(f"   Attempt {i+1}/20: Current status is '{status}'...")

                if status == "completed":
                    # FINAL FIX: The URL is directly available under the "gammaUrl" key.
                    gamma_url = status_data.get("gammaUrl")
                    if gamma_url:
                        print("\n✅ Success! Your presentation is ready:", gamma_url)
                        return # Exit successfully!
                    else:
                        print("⚠️ 'completed' status received, but the 'gammaUrl' key was not found. Full response:")
                        print(json.dumps(status_data, indent=2))
                        return

                elif status == "failed":
                    print("⚠️ Generation failed. Reason:", status_data.get("reason"))
                    return

            print("⏰ Timed out after 100 seconds waiting for generation to complete.")

        except requests.exceptions.HTTPError as e:
            print(f"⚠️ Gamma API error. Status Code: {e.response.status_code}")
            print("   Response:", e.response.text)
        except Exception as e:
            print(f"⚠️ A general error occurred during Gamma upload: {e}")
    elif not slides:
         print("⏩ Skipping Gamma upload because no slides were parsed.")
    else:
        print("⚠️ Missing GAMMA_API_KEY, skipping Gamma upload.")

    return slides, metrics

if __name__ == "__main__":
    print("---- Fetching results ----")
    summary = fetch_all(URL)

    if not summary:
        print("❌ Could not fetch data. Aborting.")
    else:
        print("---- Sending to Ollama ----")
        raw_output = run_ollama(summary)

        print("=== RAW LLM OUTPUT (preview) ===")
        print(raw_output[:500], "...\n")

        parse_and_upload(raw_output)