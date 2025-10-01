# backend/storage/__init__.py
import os
import json
import uuid
from threading import Lock
from fastapi import UploadFile
import io
import zipfile
import shutil

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "files")
JOBS_FILE = os.path.join(STORAGE_DIR, "jobs.json")
_LOCK = Lock()

os.makedirs(STORAGE_DIR, exist_ok=True)

def _load_jobs():
    if not os.path.exists(JOBS_FILE):
        return {}
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def _save_jobs(jobs):
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

def create_job(metadata: dict) -> str:
    """
    Create a job and reserve a folder for it. Returns job_id.
    """
    with _LOCK:
        jobs = _load_jobs()
        job_id = uuid.uuid4().hex
        job_dir = os.path.join(STORAGE_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        jobs[job_id] = {
            "id": job_id,
            "status": "QUEUED",
            "metadata": metadata,
            "job_dir": job_dir
        }
        _save_jobs(jobs)
    return job_id

def save_upload_and_extract(upload_file: UploadFile, job_id: str):
    """
    Save uploaded file bytes into the job folder. If the file is a ZIP, extract it.
    Returns list of saved file paths.
    """
    jobs = _load_jobs()
    job = jobs.get(job_id)
    if not job:
        raise KeyError("job not found")

    job_dir = job.get("job_dir")
    if not job_dir:
        job_dir = os.path.join(STORAGE_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

    # read bytes
    upload_file.file.seek(0)
    data = upload_file.file.read()
    # ensure filename
    filename = upload_file.filename or f"upload-{uuid.uuid4().hex}"
    dest_path = os.path.join(job_dir, filename)

    # Write the uploaded file bytes
    with open(dest_path, "wb") as f:
        f.write(data)

    saved_paths = []

    # Check if it's a zip
    try:
        bio = io.BytesIO(data)
        if zipfile.is_zipfile(bio):
            # extract into job_dir into a subfolder 'extracted'
            extracted_dir = os.path.join(job_dir, "extracted")
            # if exists, clear to avoid stale files
            if os.path.exists(extracted_dir):
                shutil.rmtree(extracted_dir)
            os.makedirs(extracted_dir, exist_ok=True)
            with zipfile.ZipFile(bio) as zf:
                # extract only files (skip directories)
                for member in zf.namelist():
                    # skip hidden/system files and directories
                    if member.endswith("/") or member.startswith("__MACOSX") or member.startswith("."):
                        continue
                    # sanitize path - use basename to avoid nested paths for safety
                    member_name = os.path.basename(member)
                    if not member_name:
                        continue
                    target_path = os.path.join(extracted_dir, member_name)
                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    saved_paths.append(target_path)
            # optionally remove the original zip file to save space
            os.remove(dest_path)
        else:
            # not a zip; saved file stays in job_dir
            saved_paths.append(dest_path)
    except Exception as e:
        # fallback: treat as single file
        saved_paths.append(dest_path)

    # update job metadata with saved paths
    with _LOCK:
        jobs = _load_jobs()
        job = jobs.get(job_id)
        if job is None:
            raise KeyError("job not found on update")
        job["saved_paths"] = saved_paths
        jobs[job_id] = job
        _save_jobs(jobs)

    return saved_paths

def save_file(upload_file: UploadFile) -> str:
    """
    Legacy single-file save (keeps compatibility). Saves to STORAGE_DIR root.
    """
    filename = upload_file.filename or f"upload-{uuid.uuid4().hex}"
    dest = os.path.join(STORAGE_DIR, filename)
    upload_file.file.seek(0)
    with open(dest, "wb") as f:
        f.write(upload_file.file.read())
    return dest

def update_job_status(job_id: str, status: str, results: dict = None, error: str = None):
    with _LOCK:
        jobs = _load_jobs()
        job = jobs.get(job_id)
        if not job:
            raise KeyError("job not found")
        job["status"] = status
        if results is not None:
            job["results"] = results
        if error:
            job["error"] = error
        jobs[job_id] = job
        _save_jobs(jobs)

def load_job(job_id: str):
    jobs = _load_jobs()
    return jobs.get(job_id)
