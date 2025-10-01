# backend/api/results.py
from fastapi import APIRouter, HTTPException
from storage import load_job

router = APIRouter()

@router.get("/{job_id}")
def get_results(job_id: str):
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "DONE":
        return {"jobId": job_id, "status": job.get("status"), "results": None}
    # return results object
    return {"jobId": job_id, "status": "DONE", "results": job.get("results")}
