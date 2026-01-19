"""
QuizAttempt model - stores quiz submissions and grading
"""
from sqlalchemy import Column, TIMESTAMP, DECIMAL, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
import uuid


class QuizAttempt(Base):
    """
    Quiz attempts table - stores user submissions and grading results
    """
    __tablename__ = "quiz_attempts"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    answers = Column(JSONB)  # User's answers
    scores = Column(JSONB)  # Per-question scores and feedback
    total_score = Column(DECIMAL(4, 2))  # Total score
    weak_topics = Column(JSONB)  # Identified weak areas
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))
    
    def __repr__(self):
        return f"<QuizAttempt(user_id={self.user_id}, quiz_id={self.quiz_id}, score={self.total_score})>"