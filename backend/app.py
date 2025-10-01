# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import ingest, status, results

app = FastAPI(title="DocuCheck - Missing Document Types (POC)")

# include routers
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(results.router, prefix="/results", tags=["results"])

# CORS for local development / Salesforce proxying if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
