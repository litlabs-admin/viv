"""
Document Verification System - Backend API

FastAPI application that provides endpoints for uploading,
verifying, and retrieving results for document verification.

Run with: uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from config import UPLOAD_DIR, OUTPUT_DIR
from routers import upload, verify, results, history


@asynccontextmanager
async def lifespan(app):
    """Initialize database on startup."""
    init_db()
    print("Database initialized.")
    print("Document Verification System API is running.")
    print("Swagger docs: http://localhost:8000/docs")
    yield


# Create FastAPI app
app = FastAPI(
    title="Document Verification System",
    description="AI-powered document verification for SPPU Marksheets, Aadhaar, PAN, and Experience Certificates",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded and output files as static
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# Include routers
app.include_router(upload.router)
app.include_router(verify.router)
app.include_router(results.router)
app.include_router(history.router)


@app.get("/")
async def root():
    return {
        "name": "Document Verification System",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
