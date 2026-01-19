"""
Pydantic schemas for analytics endpoints
"""
from pydantic import BaseModel
from typing import List, Dict, Any
from uuid import UUID


class TopicMastery(BaseModel):
    """Mastery level for a specific topic"""
    topic: str
    mastery_percentage: float
    attempts: int
    avg_score: float


class ChapterProgress(BaseModel):
    """Progress summary for a chapter"""
    chapter_id: UUID
    chapter_title: str
    completion_percentage: float
    is_completed: bool
    time_spent: int
    quiz_attempts: int
    avg_quiz_score: float


class UserPerformance(BaseModel):
    """Complete user performance analytics"""
    user_id: UUID
    total_chapters: int
    completed_chapters: int
    total_quiz_attempts: int
    overall_avg_score: float
    topic_mastery: List[TopicMastery]
    chapter_progress: List[ChapterProgress]
    weak_areas: List[str]
    recommendations: List[str]


class QuestionAnalytics(BaseModel):
    """Analytics for a specific question"""
    q_id: str
    question_text: str
    topic: str
    attempts: int
    avg_score: float
    common_mistakes: List[str]


class ChapterAnalytics(BaseModel):
    """Analytics for a specific chapter"""
    chapter_id: UUID
    chapter_title: str
    total_attempts: int
    unique_users: int
    avg_score: float
    avg_completion_time: int
    difficult_questions: List[QuestionAnalytics]
    common_weak_topics: List[Dict[str, Any]]
    completion_rate: float