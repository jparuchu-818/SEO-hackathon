# backend/combine_results.py
import os, json, subprocess, requests, pathlib

BASE = "http://127.0.0.1:8000"
URL = "https://atyalabs.com"   # test site
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_all(url: str):
    """Fetch results from all three endpoints"""
    data = {}
    try:
        data["onpage"] = requests.get(f"{BASE}/onpage", params={"url": url}).json()
        data["crawlability"] = requests.get(f"{BASE}/crawl", params={"url": url}).json()
        data["performance"] = requests.get(f"{BASE}/performance", params={"url": url}).json()
    except Exception as e:
        print("⚠️ Error fetching:", e)
    return data

def run_ollama(summary: dict) -> str:
    """Send combined JSON to Ollama and return raw output"""
    prompt = f"""
You are an expert SEO analyst. Using ONLY the JSON data below, generate a full structured report.

### OUTPUT FORMAT (MANDATORY)

1. Slides Section:
   ### SLIDES START
   - Exactly 8 slides
   - Each slide begins with: ## Slide X: Title
   - Each slide must have 6–8 bullet points
   - Each bullet = **data + explanation + implication**
   - Use only numbers/text from the JSON (e.g., word count, link counts, CWV, scores, keywords)
   - End each slide with a **Key Takeaway**
   ### SLIDES END

2. Metrics Section:
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

### IMPORTANT
- Do NOT invent numbers.
- Always produce all 8 slides and also make sure to prduce JSON for the metrcis clear and concise.
- Do NOT skip or cut off content.

### JSON INPUT
{json.dumps(summary, indent=2)}
"""
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt.encode("utf-8"),
        capture_output=True,
    )
    return result.stdout.decode("utf-8")

def parse_output(raw_output: str):
    """Split Ollama output into slides and metrics JSON"""
    slides = ""
    metrics = "{}"

    # Extract slides
    if "### SLIDES START" in raw_output and "### SLIDES END" in raw_output:
        slides = raw_output.split("### SLIDES START",1)[1].split("### SLIDES END",1)[0].strip()

    # Extract metrics
    if "### METRICS START" in raw_output and "### METRICS END" in raw_output:
        metrics = raw_output.split("### METRICS START",1)[1].split("### METRICS END",1)[0].strip()

    # Save slides
    (OUT_DIR / "seo_report.md").write_text(slides)

    # Save metrics
    try:
        metrics_json = json.loads(metrics)
        (OUT_DIR / "seo_metrics.json").write_text(json.dumps(metrics_json, indent=2))
    except Exception:
        print("⚠️ Metrics JSON parse failed")
        (OUT_DIR / "seo_metrics.json").write_text("{}")

    # Count slides flexibly (## or ####)
    num_slides = slides.count("## Slide") + slides.count("#### Slide")
    print(f"✅ Saved: {num_slides} slides, metrics to reports/")
    return slides, metrics


if __name__ == "__main__":
    print("---- Fetching results ----")
    summary = fetch_all(URL)

    print("---- Sending to Ollama ----")
    raw_output = run_ollama(summary)

    print("=== RAW LLM OUTPUT (preview) ===")
    print(raw_output[:500], "...\n")

    parse_output(raw_output)
