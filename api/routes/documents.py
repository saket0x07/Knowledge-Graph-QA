from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
import os
import shutil
from pathlib import Path
from services.ingestion import process_document

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
    
    # Trigger processing in the background
    background_tasks.add_task(process_document, str(file_path))
    
    return {"message": f"Successfully uploaded {file.filename}. Processing started.", "file_path": str(file_path)}
