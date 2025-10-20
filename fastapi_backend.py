#!/usr/bin/env python3
"""
FastAPI backend for the AI RFP Assistant.
This provides API endpoints for file serving, content loading, and other backend operations.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import json
from datetime import datetime
import uuid

# Import our services
from services.s3_client import s3_client
from services.dynamodb_client import dynamodb_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI RFP Assistant API",
    description="Backend API for the AI RFP Assistant application",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("public"):
    app.mount("/public", StaticFiles(directory="public"), name="public")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI RFP Assistant API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if services are available
        services_status = {
            "s3_client": "available",
            "dynamodb_client": "available",
            "timestamp": datetime.now().isoformat()
        }
        return {"status": "healthy", "services": services_status}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/load-content")
async def load_content(request: Request):
    """Load content from storage."""
    try:
        data = await request.json()
        content_key = data.get("content_key")
        session_id = data.get("session_id")
        
        if not content_key:
            raise HTTPException(status_code=400, detail="content_key is required")
        
        # Load content from S3
        content_data = s3_client.download_file_object(content_key)
        if content_data:
            content = content_data.decode('utf-8')
            logger.info(f"✅ Loaded content from S3: {content_key}")
            return {"content": content, "size": len(content)}
        else:
            logger.error(f"❌ Failed to load content from S3: {content_key}")
            raise HTTPException(status_code=404, detail="Content not found")
            
    except Exception as e:
        logger.error(f"❌ Error loading content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/canvas/{filename}")
async def serve_canvas_file(filename: str):
    """Serve canvas files."""
    file_path = os.path.join("public", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.error(f"❌ Canvas file not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session data."""
    try:
        data = dynamodb_client.get_session_data(session_id)
        if data:
            return {"session_id": session_id, "data": data}
        else:
            return {"session_id": session_id, "data": {}}
    except Exception as e:
        logger.error(f"❌ Error getting session data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/{session_id}")
async def save_session(session_id: str, request: Request):
    """Save session data."""
    try:
        data = await request.json()
        success = dynamodb_client.save_session_data(session_id, data)
        if success:
            return {"status": "success", "session_id": session_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save session data")
    except Exception as e:
        logger.error(f"❌ Error saving session data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/list")
async def list_storage():
    """List files in storage."""
    try:
        # This would need to be implemented in s3_client
        return {"message": "Storage listing not implemented yet"}
    except Exception as e:
        logger.error(f"❌ Error listing storage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
