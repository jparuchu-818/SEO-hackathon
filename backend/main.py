from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from core.logic import generate_presentation

app = FastAPI()

class InputText(BaseModel):
    text: str

@app.post("/generate")
def generate_presentation_api(input: InputText):
    filename = generate_presentation(input.text)
    return FileResponse(filename, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="output.pptx")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
