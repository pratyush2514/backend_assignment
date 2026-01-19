"""
Pydantic schemas for chapter-related requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class ChapterCreate(BaseModel):
    """Schema for uploading a new chapter"""
    subject: str = Field(..., max_length=50, description="Subject name")
    class_level: int = Field(..., ge=1, le=12, description="Class level (1-12)")
    title: str = Field(..., max_length=255, description="Chapter title")


class ChapterResponse(BaseModel):
    """Response after chapter upload"""
    chapter_id: UUID
    status: str = "indexed"
    gemini_file_id: str
    title: str
    
    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    """Schema for updating chapter progress"""
    user_id: UUID
    time_spent: int = Field(..., ge=0, description="Time spent in seconds")
    scroll_pct: float = Field(..., ge=0.0, le=100.0, description="Scroll percentage")
    selections: Optional[int] = Field(0, ge=0, description="Number of text selections")


class ProgressResponse(BaseModel):
    """Response for progress update"""
    message: str
    is_completed: bool
    completion_pct: float


class ChapterStatus(BaseModel):
    """Chapter completion status"""
    completion_pct: float
    is_completed: bool
    method_used: str
    time_spent: Optional[int] = None
    scroll_progress: Optional[float] = None
    
    class Config:
        from_attributes = True