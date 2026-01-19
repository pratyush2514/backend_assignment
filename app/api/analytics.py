"""
Performance analytics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.database import get_db
from app.schemas.analytics import UserPerformance, ChapterAnalytics
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/api", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get("/users/{user_id}/performance", response_model=UserPerformance)
async def get_user_performance(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive performance analytics for a user
    
    Returns:
    - Overall statistics (chapters, quizzes, avg score)
    - Topic mastery breakdown
    - Chapter-wise progress
    - Weak areas identification
    - Personalized recommendations
    """
    
    try:
        logger.info(f"Fetching performance analytics for user {user_id}")
        
        performance = analytics_service.get_user_performance(db, user_id)
        
        return UserPerformance(**performance)
        
    except Exception as e:
        logger.error(f"Failed to fetch user performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch performance analytics: {str(e)}"
        )


@router.get("/chapters/{chapter_id}/analytics", response_model=ChapterAnalytics)
async def get_chapter_analytics(
    chapter_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get analytics for a specific chapter
    
    Returns:
    - Total attempts and unique users
    - Average score and completion time
    - Difficult questions (low avg scores)
    - Common weak topics
    - Completion rate
    """
    
    try:
        logger.info(f"Fetching analytics for chapter {chapter_id}")
        
        analytics = analytics_service.get_chapter_analytics(db, chapter_id)
        
        if analytics is None:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        return ChapterAnalytics(**analytics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch chapter analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch chapter analytics: {str(e)}"
        )