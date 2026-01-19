"""
Chapter management API endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import aiofiles
import os
import logging
from typing import Optional

from app.database import get_db
from app.models import Chapter, UserProgress
from app.schemas.chapter import (
    ChapterCreate, ChapterResponse, ProgressUpdate,
    ProgressResponse, ChapterStatus
)
from app.services.gemini_service import gemini_service
from app.services.completion_service import completion_service
from app.utils.rate_limiter import rate_limiter

router = APIRouter(prefix="/api/chapters", tags=["chapters"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChapterResponse, status_code=201)
async def upload_chapter(
    file: UploadFile = File(...),
    subject: str = Form(...),
    class_level: int = Form(...),
    title: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload a chapter PDF and index it with Gemini
    
    - Validates PDF file
    - Uploads to Gemini File API
    - Extracts topics
    - Stores metadata in database
    """
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate class level
    if not 1 <= class_level <= 12:
        raise HTTPException(status_code=400, detail="Class level must be between 1 and 12")
    
    try:
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Uploading chapter PDF: {file.filename}")
        
        # Upload to Gemini and extract topics
        gemini_file_id, topics = gemini_service.upload_and_index_pdf(
            temp_path,
            display_name=f"{subject}_{class_level}_{title}"
        )
        
        # Create chapter record
        chapter = Chapter(
            gemini_file_id=gemini_file_id,
            subject=subject,
            class_level=class_level,
            title=title,
            topics=topics,
            status="indexed"
        )
        
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        
        logger.info(f"Chapter created: {chapter.id}")
        
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return ChapterResponse(
            chapter_id=chapter.id,
            status=chapter.status,
            gemini_file_id=chapter.gemini_file_id,
            title=chapter.title
        )
        
    except Exception as e:
        logger.error(f"Failed to upload chapter: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.put("/{chapter_id}/progress", response_model=ProgressResponse)
async def update_progress(
    chapter_id: UUID,
    progress: ProgressUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user's chapter progress and calculate completion
    
    Uses multi-factor algorithm:
    - Time spent (30%)
    - Scroll progress (40%)
    - Interactions (30%)
    
    Threshold: 75% composite score
    """
    
    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Find existing progress or create new
    user_progress = db.query(UserProgress).filter(
        UserProgress.user_id == progress.user_id,
        UserProgress.chapter_id == chapter_id
    ).first()
    
    if not user_progress:
        user_progress = UserProgress(
            user_id=progress.user_id,
            chapter_id=chapter_id
        )
        db.add(user_progress)
    
    # Update progress fields
    user_progress.time_spent = progress.time_spent
    user_progress.scroll_progress = progress.scroll_pct
    
    # Calculate completion using algorithm
    is_completed, completion_pct, method_used = completion_service.calculate_completion(
        time_spent=progress.time_spent,
        scroll_pct=progress.scroll_pct,
        selections=progress.selections,
        estimated_pages=10  # Default estimate
    )
    
    user_progress.is_completed = is_completed
    user_progress.completion_method = method_used
    
    db.commit()
    
    logger.info(
        f"Progress updated: user={progress.user_id}, chapter={chapter_id}, "
        f"completed={is_completed}, score={completion_pct:.2f}"
    )
    
    return ProgressResponse(
        message="Progress updated successfully",
        is_completed=is_completed,
        completion_pct=round(completion_pct * 100, 2)
    )


@router.get("/{chapter_id}/status", response_model=ChapterStatus)
async def get_chapter_status(
    chapter_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get chapter completion status for a user
    
    Returns:
    - Completion percentage
    - Completion status
    - Method used for detection
    """
    
    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Get user progress
    user_progress = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.chapter_id == chapter_id
    ).first()
    
    if not user_progress:
        return ChapterStatus(
            completion_pct=0.0,
            is_completed=False,
            method_used="no_progress",
            time_spent=0,
            scroll_progress=0.0
        )
    
    # Calculate current completion score
    _, completion_pct, method_used = completion_service.calculate_completion(
        time_spent=user_progress.time_spent or 0,
        scroll_pct=float(user_progress.scroll_progress or 0),
        selections=0,  # Not tracked in status check
        estimated_pages=10
    )
    
    return ChapterStatus(
        completion_pct=round(completion_pct * 100, 2),
        is_completed=user_progress.is_completed,
        method_used=user_progress.completion_method or method_used,
        time_spent=user_progress.time_spent,
        scroll_progress=float(user_progress.scroll_progress) if user_progress.scroll_progress else 0.0
    )