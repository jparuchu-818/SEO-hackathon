from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from core.logic import generate_presentation


# Person A
from backend.onpage import router as onpage_router
# Person C
from crawlability_checker import crawlability_audit
# Person B
from backend.performance import performance_audit  

app = FastAPI()
app.include_router(onpage_router)

class InputText(BaseModel):
    text: str

@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}

@app.get("/crawl")
def crawl(url: str):
    return crawlability_audit(url)

@app.get("/performance")
def performance(url: str):
    return performance_audit(url)

@app.post("/generate")
def generate_presentation_api(input: InputText):
    filename = generate_presentation(input.text)
    return FileResponse(filename, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="output.pptx")
