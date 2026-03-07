"""
Minimal FastAPI entry point for Render deployment
Bypasses complex dependencies to ensure successful build
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Resume Verification API - Minimal")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "service": "Resume Verification API",
        "status": "operational",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "message": "Minimal deployment - ready for configuration"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "database": "not_configured",
        "redis": "not_configured"
    }

@app.get("/api/status")
def status():
    return {
        "service": "resume-verify-backend",
        "version": "1.0.0-minimal",
        "ready_for": "environment_variable_configuration"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
