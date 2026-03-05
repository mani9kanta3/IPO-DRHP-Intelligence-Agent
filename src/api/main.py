import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from pathlib import Path
from src.api.schemas import AnalysisStatus, AnalysisReport

app = FastAPI(title="IPO DRHP Intelligence Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# In-memory job store
jobs = {}
        
def run_pipeline(job_id: str, pdf_path: str, file_name: str):
    try:
        jobs[job_id]["status"] = "analyzing"
        jobs[job_id]["message"] = "Running AI agents..."

        from src.graph.workflow import run_analysis
        final_state, elapsed = run_analysis(pdf_path)

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["message"] = f"Analysis complete in {elapsed} seconds!"
        jobs[job_id]["result"] = final_state

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"
        print(f"Pipeline error for job {job_id}: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "message": "DRHP Agent API is running"}


@app.post("/analyze", response_model=AnalysisStatus)
async def analyze(file: UploadFile = File(...)):
    # Validate file
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    file_size = 0
    contents = await file.read()
    file_size = len(contents) / (1024 * 1024)  # MB

    if file_size > 50:
        raise HTTPException(status_code=400, detail="File too large. Max 50MB.")

    # Save uploaded file
    job_id = str(uuid.uuid4())[:8]
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(exist_ok=True)
    pdf_path = str(upload_dir / f"{job_id}_{file.filename}")

    with open(pdf_path, "wb") as f:
        f.write(contents)

    # Initialize job
    jobs[job_id] = {
        "status": "queued",
        "message": "Analysis queued",
        "result": None
    }

    # Run pipeline in background
    import threading
    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, pdf_path, file.filename)
    )
    thread.start()

    return AnalysisStatus(
        job_id=job_id,
        status="queued",
        message="Analysis started. Poll /status/{job_id} for updates."
    )


@app.get("/status/{job_id}", response_model=AnalysisStatus)
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return AnalysisStatus(
        job_id=job_id,
        status=job["status"],
        message=job["message"]
    )


@app.get("/report/{job_id}", response_model=AnalysisReport)
def get_report(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail=f"Analysis not complete. Status: {job['status']}")

    state = job["result"]
    financials = state.get("financials", {})

    return AnalysisReport(
        job_id=job_id,
        company=state.get("file_name", "").replace(".pdf", ""),
        verdict=state.get("verdict", ""),
        risk_score=state.get("risk_score", 0),
        financial_health_score=financials.get("health_score", 0),
        red_flags=state.get("red_flags", []),
        promoter_report=state.get("promoter_report", []),
        valuation=state.get("valuation", {}),
        financials=financials,
        final_report=state.get("final_report", ""),
        total_pages=state.get("total_pages", 0),
        status=state.get("status", ""),
        errors=state.get("errors", [])
    )