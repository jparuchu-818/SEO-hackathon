from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from core.logic import generate_presentation
from backend.onpage import router as onpage_router
from crawlability_checker import crawlability_audit

app = FastAPI()
app.include_router(onpage_router)


class InputText(BaseModel):
    text: str

@app.post("/generate")
def generate_presentation_api(input: InputText):
    filename = generate_presentation(input.text)
    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="output.pptx"
    )

@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}

@app.get("/crawl")
def crawl(url: str):
    return crawlability_audit(url)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
