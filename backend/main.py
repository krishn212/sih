"""
Legal Metrology Compliance Scanner — FastAPI Backend
Entry point: main.py
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

from models.database import create_tables
from routes import auth, scan, reports, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables if they don't exist."""
    try:
        create_tables()
    except Exception as e:
        print(f"Non-blocking startup notice: {e}")
    # Ensure upload/report directories exist
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    yield


app = FastAPI(
    title="Legal Metrology Compliance Scanner",
    description="AI-assisted, evidence-backed digital inspection system for Legal Metrology enforcement.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React dev server and any deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist before mounting
for _d in ["uploads", "reports", "demo_samples"]:
    os.makedirs(_d, exist_ok=True)

# Serve uploaded images and generated reports as static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
app.mount("/demo_samples", StaticFiles(directory="demo_samples"), name="demo_samples")

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(scan.router, prefix="/scan", tags=["Scanning"])
app.include_router(scan.router, prefix="/scans", tags=["Scanning"])
app.include_router(reports.router, prefix="/report", tags=["Reports"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "Legal Metrology Compliance Scanner",
        "version": "1.0.0",
    }
