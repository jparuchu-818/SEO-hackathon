from fastapi import FastAPI
from backend.crawlability_checker import crawlability_audit
from backend.onpage import router as onpage_router


app = FastAPI()

# Person A's onpage router
app.include_router(onpage_router)

# Person C's crawl endpoint
@app.get("/crawl")
def crawl(url: str):
    return crawlability_audit(url)

@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}
