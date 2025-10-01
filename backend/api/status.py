# backend/api/status.py
from fastapi import APIRouter, HTTPException
from storage import load_job

router = APIRouter()

@router.get("/{job_id}")
def get_status(job_id: str):
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"jobId": job_id, "status": job.get("status", "UNKNOWN"), "error": job.get("error")}
