# backend/analyzer.py
import os, sys, json, time, requests, datetime, pathlib, urllib.parse

PSI_BASE = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
API_KEY = os.getenv("GOOGLE_API_KEY")

CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "psi"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _slug(url: str) -> str:
    p = urllib.parse.urlparse(url)
    host = (p.netloc or p.path).lower().strip("/").replace(":", "_")
    return host or "unknown"

def _cache_path(url: str, strategy: str) -> pathlib.Path:
    return CACHE_DIR / f"{_slug(url)}__{strategy}.json"

def _fetch_pagespeed(url: str, strategy: str, retries: int = 3, refresh: bool = False) -> dict:
    if not API_KEY:
        raise RuntimeError('GOOGLE_API_KEY not set. Run: export GOOGLE_API_KEY="YOUR_KEY"')

    cp = _cache_path(url, strategy)
    if cp.exists() and not refresh:
        return json.loads(cp.read_text())

    params = {"url": url, "strategy": strategy, "key": API_KEY}
    backoff = 1.0
    for _ in range(retries):
        r = requests.get(PSI_BASE, params=params, timeout=(10, 180))
        if r.status_code == 200:
            data = r.json()
            cp.write_text(json.dumps(data, ensure_ascii=False))
            return data
        # show helpful error details
        try:
            err = r.json()
        except Exception:
            err = {"text": r.text}
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(backoff); backoff *= 2; continue
        raise RuntimeError(f"PSI {strategy} HTTP {r.status_code}: {err}")
    raise RuntimeError(f"PSI {strategy} failed after retries")

def _safe_score(cats, key):
    cat = (cats or {}).get(key) or (cats or {}).get(key.replace("-", ""))
    return int(round((cat.get("score", 0) or 0) * 100)) if cat else 0

def _labels_for_cwv(lcp_ms, inp_ms, cls):
    def lcp(v): return None if v is None else ("good" if v <= 2500 else "needs_improvement" if v <= 4000 else "poor")
    def inp(v): return None if v is None else ("good" if v <= 200 else "needs_improvement" if v <= 500 else "poor")
    def clsf(v): return None if v is None else ("good" if v <= 0.10 else "needs_improvement" if v <= 0.25 else "poor")
    return {"lcp": lcp(lcp_ms), "inp": inp(inp_ms), "cls": clsf(cls)}

def _extract_block(psi_json: dict) -> dict:
    lhr = psi_json.get("lighthouseResult") or {}
    cats = lhr.get("categories") or {}
    audits = lhr.get("audits") or {}

    scores = {
        "performance": _safe_score(cats, "performance"),
        "seo": _safe_score(cats, "seo"),
        "accessibility": _safe_score(cats, "accessibility"),
        "best_practices": _safe_score(cats, "best-practices"),
    }

    lcp = (audits.get("largest-contentful-paint") or {}).get("numericValue")
    cls = (audits.get("cumulative-layout-shift") or {}).get("numericValue")
    inp = None
    if "interaction-to-next-paint" in audits:
        inp = audits["interaction-to-next-paint"].get("numericValue")
    elif "experimental-interaction-to-next-paint" in audits:
        inp = audits["experimental-interaction-to-next-paint"].get("numericValue")

    # collect biggest opportunities
    opps = []
    for k, v in (audits or {}).items():
        d = v.get("details")
        if isinstance(d, dict) and d.get("type") == "opportunity":
            opps.append((d.get("overallSavingsMs") or 0, v.get("title") or k))
    opps.sort(reverse=True, key=lambda x: x[0])

    return {
        "scores": scores,
        "lab_cwv": {
            "lcp_ms": int(round(lcp)) if isinstance(lcp, (int, float)) else None,
            "inp_ms": int(round(inp)) if isinstance(inp, (int, float)) else None,
            "cls": float(cls) if isinstance(cls, (int, float)) else None,
            "labels": _labels_for_cwv(lcp, inp, cls)
        },
        "top_opportunities": [t for _, t in opps[:5]]
    }

def analyze(url: str, refresh: bool = False) -> dict:
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    mobile = _fetch_pagespeed(url, "mobile", refresh=refresh)
    desktop = _fetch_pagespeed(url, "desktop", refresh=refresh)
    return {
        "url": url,
        "pagespeed": {
            "mobile": _extract_block(mobile),
            "desktop": _extract_block(desktop),
        },
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    refresh = "--refresh" in sys.argv
    print(json.dumps(analyze(url, refresh=refresh), indent=2))
