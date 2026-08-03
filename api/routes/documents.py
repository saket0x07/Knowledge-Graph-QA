from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
import os
import shutil
from pathlib import Path
from services.ingestion import process_document
from db.sqlite_client import log_ingestion_start, get_ingestion_history

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_path = UPLOAD_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Log start to DB
    file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
    log_ingestion_start(file.filename, file_size_mb)
    
    # Trigger processing in the background
    background_tasks.add_task(process_document, str(file_path))
    
    return {"message": f"Successfully uploaded {file.filename}. Processing started.", "file_path": str(file_path), "filename": file.filename}

@router.get("/history")
async def fetch_history():
    return get_ingestion_history()

@router.get("/status/{filename}")
async def get_document_status(filename: str):
    from services.ingestion import processing_status
    status = processing_status.get(filename, "not_found")
    return {"filename": filename, "status": status}
