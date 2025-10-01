# backend/api/ingest.py
import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List

from storage import create_job, update_job_status, save_upload_and_extract, load_job
from ocr.tesseract import extract_text_from_path
from classifiers.heuristics import classify_texts, classify_single_text

router = APIRouter()

@router.post("/")
async def ingest(
    loanIntakeId: str = Form(...),
    program: str = Form(...),
    milestone: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Ingest a single ZIP/PDF/image or raw file. For this POC we accept a single upload
    which can be a zip containing multiple files.
    Returns: { jobId, status }
    """
    # Create job first so we have a folder
    job_id = create_job({
        "loanIntakeId": loanIntakeId,
        "program": program,
        "milestone": milestone
    })

    # Save or extract files into job folder
    try:
        saved_paths = save_upload_and_extract(file, job_id)
    except Exception as e:
        update_job_status(job_id, "FAILED", error=f"failed to save/upload: {e}")
        raise HTTPException(status_code=500, detail=f"failed to save file: {e}")

    # mark in-progress
    update_job_status(job_id, "IN_PROGRESS")

    # Process each saved path: OCR -> classification
    try:
        all_texts = []  # list of (source_name, text)
        for path in saved_paths:
            # extract_text_from_path returns list of (name, text) already
            results = extract_text_from_path(path)
            # results could be multi-page; append all
            all_texts.extend(results)

        if not all_texts:
            # no text found; mark empty
            update_job_status(job_id, "DONE", results={"found": [], "summary": {"found_types": [], "file_count": 0}})
            return {"jobId": job_id, "status": "DONE"}

        # classify each text/page
        findings = []
        for fname, txt in all_texts:
            label, score, reasons, snippet = classify_single_text(txt)
            findings.append({
                "file": os.path.basename(fname),
                "type": label,
                "confidence": round(float(score), 3),
                "reasons": reasons,
                "snippet": snippet
            })

        # summary via classify_texts helper
        summary = classify_texts(all_texts)

        # persist results
        update_job_status(job_id, "DONE", results={"found": findings, "summary": summary, "saved_paths": saved_paths})
    except Exception as e:
        update_job_status(job_id, "FAILED", error=str(e))
        raise HTTPException(status_code=500, detail=f"processing failed: {e}")

    return {"jobId": job_id, "status": "DONE"}
