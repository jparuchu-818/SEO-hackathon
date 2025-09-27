from fastapi import FastAPI
from crawlability_checker import crawlability_audit

app = FastAPI()

@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}

@app.get("/crawl")
def crawl(url: str):
    return crawlability_audit(url)
