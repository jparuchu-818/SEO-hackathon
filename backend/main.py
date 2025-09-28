# backend/main.py
import os, sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# allow importing core/ from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.logic import generate_presentation

from .analyzer import analyze as analyze_pagespeed

# add this endpoint below /health


# allow importing core/ from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.logic import generate_presentation  # keep this import

app = FastAPI(
    title="SEO Hackathon API",
    version="0.1.0",
    docs_url="/docs",    # Swagger UI
    redoc_url="/redoc",  # ReDoc (backup docs)
    openapi_url="/openapi.json"
)

class InputText(BaseModel):
    text: str

@app.get("/")
def root():
    return {"ok": True, "visit": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate_presentation_api(input: InputText):
    filename = generate_presentation(input.text)
    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="output.pptx"
    )
@app.get("/pagespeed")
def pagespeed(url: str, refresh: bool = False):
    try:
        return analyze_pagespeed(url, refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# run with: uvicorn backend.main:app --reload --port 8000
