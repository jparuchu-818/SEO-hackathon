# backend/analyzer.py
"""
Person B: PageSpeed Insights integration (robust)
- Requests ALL Lighthouse categories
- Longer read timeout + retries with backoff
- Caches raw PSI JSON in data/psi/
- Returns partial results when one strategy fails (adds `errors`)
"""

from __future__ import annotations
import os, sys, json, time, datetime, pathlib, urllib.parse
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv
load_dotenv()

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


def _fetch_pagespeed(url: str, strategy: str, retries: int = 5, refresh: bool = False) -> Dict[str, Any]:
    if not API_KEY:
        raise RuntimeError('GOOGLE_API_KEY not set. Run: export GOOGLE_API_KEY="YOUR_KEY"')

    cp = _cache_path(url, strategy)
    if cp.exists() and not refresh:
        return json.loads(cp.read_text())

    params = {
        "url": url,
        "strategy": strategy,
        "key": API_KEY,
        "category": ["performance", "seo", "accessibility", "best-practices"],
    }

    backoff = 1.0
    last_err = None
    for _ in range(retries):
        r = requests.get(PSI_BASE, params=params, timeout=(10, 180))
        if r.status_code == 200:
            data = r.json()
            cp.write_text(json.dumps(data, ensure_ascii=False))
            return data

        try:
            err = r.json()
        except Exception:
            err = {"text": r.text}
        last_err = f"HTTP {r.status_code}: {err}"

        # retry on throttling / transient errors
        if r.status_code in (408, 429, 500, 502, 503, 504):
            time.sleep(backoff)
            backoff = min(backoff * 2, 16)
            continue

        # non-retriable
        raise RuntimeError(f"PSI {strategy} {last_err}")

    raise RuntimeError(f"PSI {strategy} failed after retries: {last_err}")


def _safe_score(cats: Dict[str, Any], key: str) -> int:
    cat = (cats or {}).get(key) or (cats or {}).get(key.replace("-", ""))
    return int(round((cat.get("score", 0) or 0) * 100)) if cat else 0


def _labels_for_cwv(lcp_ms: Optional[float], inp_ms: Optional[float], cls: Optional[float]) -> Dict[str, Optional[str]]:
    def lcp(v): return None if v is None else ("good" if v <= 2500 else "needs_improvement" if v <= 4000 else "poor")
    def inp(v): return None if v is None else ("good" if v <= 200 else "needs_improvement" if v <= 500 else "poor")
    def clsf(v): return None if v is None else ("good" if v <= 0.10 else "needs_improvement" if v <= 0.25 else "poor")
    return {"lcp": lcp(lcp_ms), "inp": inp(inp_ms), "cls": clsf(cls)}


def _extract_block(psi_json: Dict[str, Any]) -> Dict[str, Any]:
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

    opps: List[tuple] = []
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
            "labels": _labels_for_cwv(lcp, inp, cls),
        },
        "top_opportunities": [t for _, t in opps[:5]],
    }


def analyze(url: str, refresh: bool = False, tolerate_failures: bool = True) -> Dict[str, Any]:
    """Return mobile & desktop results; keep going even if one side fails."""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    result: Dict[str, Any] = {
        "url": url,
        "pagespeed": {},
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    errors: Dict[str, str] = {}

    # mobile
    try:
        m = _fetch_pagespeed(url, "mobile", refresh=refresh)
        result["pagespeed"]["mobile"] = _extract_block(m)
    except Exception as e:
        errors["mobile"] = str(e)

    # desktop
    try:
        d = _fetch_pagespeed(url, "desktop", refresh=refresh)
        result["pagespeed"]["desktop"] = _extract_block(d)
    except Exception as e:
        errors["desktop"] = str(e)

    if errors:
        result["errors"] = errors
        if not tolerate_failures:
            raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))

    return result


if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    force = ("--refresh" in sys.argv)
    print(json.dumps(analyze(test_url, refresh=force), indent=2))