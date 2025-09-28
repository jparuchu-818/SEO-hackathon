from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Person A
from backend.onpage import router as onpage_router

# Person C
from backend.crawlability_checker import crawlability_audit

# Person B
from backend.analyzer import analyze


app = FastAPI()
app.include_router(onpage_router)


class InputText(BaseModel):
    text: str


@app.post("/generate")
def generate_presentation_api(input: InputText):
    # stub: just returns ppt if you add later
    return FileResponse("output.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="output.pptx")


@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}


# Person C
@app.get("/crawl")
def crawl(url: str):
    return crawlability_audit(url)


# Person B
@app.get("/performance")
def performance(url: str, refresh: bool = False):
    return analyze(url, refresh)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
