from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from backend.onpage import router as onpage_router, run_onpage_audit

from backend.crawlability_checker import crawlability_audit

def run_performance_audit(url: str) -> dict:
    # TODO: Replace with real PageSpeed API call
    return {
        "performance": {
            "score": "N/A",
            "notes": ["Performance module not yet implemented"]
        }
    }

# Core logic for PPT
from core.logic import generate_presentation


app = FastAPI(title="SEO Hackathon Backend")
app.include_router(onpage_router)


class InputText(BaseModel):
    text: str


@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}


# Person C standalone
@app.get("/crawl")
def crawl(url: str = Query(..., description="Website URL to audit")):
    try:
        return crawlability_audit(url)
    except Exception as e:
        return {"error": str(e)}


# Person A standalone
@app.get("/onpage")
def onpage(url: str = Query(..., description="Website URL to audit")):
    try:
        return run_onpage_audit(url)
    except Exception as e:
        return {"error": str(e)}


# Person B standalone (stub)
@app.get("/performance")
def performance(url: str = Query(..., description="Website URL to audit")):
    return run_performance_audit(url)


# Combined generator
@app.post("/generate_full")
def generate_full(url: str = Query(..., description="Website URL to audit")):
    try:
        onpage_data = run_onpage_audit(url)      # Person A
        crawl_data = crawlability_audit(url)     # Person C
        perf_data = run_performance_audit(url)   # Person B (stub)

        combined = {
            "onpage": onpage_data,
            "crawlability": crawl_data,
            "performance": perf_data
        }

        filename = generate_presentation(combined)
        return FileResponse(
            filename,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename="seo_audit_output.pptx"
        )
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
