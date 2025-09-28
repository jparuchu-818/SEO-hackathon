import uuid
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# --- Import endpoint logic from your other backend files ---
from backend.onpage import router as onpage_router
from backend.crawlability_checker import crawlability_audit
from backend.analyzer import analyze
from backend.workflow import run_full_workflow

# Initialize the FastAPI app
app = FastAPI()

# --- Add CORS Middleware ---
# This is crucial for allowing your React frontend (on localhost:3000)
# to communicate with this server (on localhost:8000).
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory storage for job statuses ---
# In a real production app, you would use a database like Redis.
job_statuses = {}

# --- Define API Endpoints ---

# Include the router from onpage.py to create the /onpage endpoint
app.include_router(onpage_router)

# The root endpoint
@app.get("/")
def root():
    return {"message": "SEO Hackathon Backend is running"}

# The crawlability endpoint that the workflow will call
@app.get("/crawl")
def crawl(url: str):
    return crawlability_audit(url)

# The performance endpoint that the workflow will call
@app.get("/performance")
def performance(url: str, refresh: bool = False):
    return analyze(url, refresh)

# Pydantic model for the frontend's request body
class ReportRequest(BaseModel):
    url: str

# The main endpoint that the frontend will call to start the process
@app.post("/generate-report")
def generate_report_endpoint(request: ReportRequest, background_tasks: BackgroundTasks):
    """Accepts a URL, starts the workflow, and returns a job ID."""
    job_id = str(uuid.uuid4())
    job_statuses[job_id] = {"status": "pending", "result": None}
    
    background_tasks.add_task(run_full_workflow, job_id, request.url, job_statuses)
    
    return {"message": "Report generation started", "job_id": job_id}

# The status-checking endpoint that the frontend will poll
@app.get("/report-status/{job_id}")
def get_report_status(job_id: str):
    """Returns the status of a specific job."""
    return job_statuses.get(job_id, {"status": "not_found", "result": None})

# --- Run the Server ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
