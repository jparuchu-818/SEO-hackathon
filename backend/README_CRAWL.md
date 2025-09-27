# Crawlability & Indexing Auditor (Person C)

This module is part of the **SEO Hackathon Backend**.  
It checks a website’s **crawlability and indexing signals**, focusing on:

- **robots.txt** rules  
- **sitemap.xml** extraction  
- **canonical & meta robots consistency**  
- **summary status** of whether the site is indexable  

---

## Features
- Downloads and parses **robots.txt** (user-agent aware).  
- Extracts sitemap locations from robots.txt or defaults to `/sitemap.xml`.  
- Parses sitemap index files and nested sitemaps (samples first 10 URLs).  
- Detects indexing signals:
  - `<meta name="robots">`
  - `<link rel="canonical">` (cross-check with Person A’s output)  
- Generates a **summary report**:
  - Fully Indexable  
  - Blocked by robots.txt  
  - No sitemap found / empty sitemap  
  - Canonical mismatch  
  - Page-level noindex  

---

## Example Output
```json
{
  "crawlability": {
    "robots_txt": {
      "allows": false,
      "disallows": ["/search", "/private"]
    },
    "sitemap_info": {
      "sitemaps_checked": ["https://example.com/sitemap.xml"],
      "sitemap_urls_sample": [
        "https://example.com/",
        "https://example.com/blog"
      ],
      "total_urls": 2
    },
    "indexing_signals": {
      "robots_meta": "index, follow",
      "canonical": "https://example.com/",
      "canonical_consistency": "Matches"
    },
    "summary": {
      "status": "Issues Found",
      "notes": [
        "Blocked by robots.txt",
        "Canonical mismatch"
      ]
    }
  }
}
