"""
Pydantic schemas for quiz-related requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID


class QuizGenerateRequest(BaseModel):
    """Request schema for quiz generation"""
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$", description="Quiz difficulty")
    num_mcq: int = Field(5, ge=1, le=10, description="Number of MCQ questions")
    num_short: int = Field(3, ge=1, le=10, description="Number of short answer questions")
    num_numerical: int = Field(2, ge=0, le=10, description="Number of numerical problems")


class QuizQuestion(BaseModel):
    """Individual quiz question"""
    q_id: str
    type: str  # mcq, short, numerical
    question: str
    options: Optional[List[str]] = None  # For MCQs
    correct_answer: Any  # Index for MCQ, text for others
    topic: str
    points: float = 1.0


class QuizResponse(BaseModel):
    """Response containing generated quiz"""
    quiz_id: UUID
    questions: List[Dict[str, Any]]
    total_questions: int
    total_points: float
    
    class Config:
        from_attributes = True


class QuizSubmission(BaseModel):
    """Schema for quiz submission"""
    user_id: UUID
    answers: Dict[str, Any]  # {q_id: answer}


class QuestionGrading(BaseModel):
    """Grading details for a single question"""
    q_id: str
    user_answer: Any
    correct_answer: Any
    score: float
    max_score: float
    feedback: Optional[str] = None
    is_correct: bool


class QuizGradingResponse(BaseModel):
    """Response after quiz grading"""
    score: float
    max_score: float
    score_display: str  # "8.5/10" format as per assignment
    percentage: float
    breakdown: List[QuestionGrading]
    weak_topics: List[str]
    feedback: str
    
    class Config:
        from_attributes = True