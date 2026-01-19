"""
Quiz model - stores generated quizzes
"""
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
import uuid


class Quiz(Base):
    """
    Quizzes table - stores generated quiz questions with caching support
    """
    __tablename__ = "quizzes"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"), nullable=False)
    difficulty = Column(String(20))
    questions = Column(JSONB, nullable=False)  # Full question data
    variant_hash = Column(String(64), index=True)  # For caching
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))
    
    def __repr__(self):
        return f"<Quiz(id={self.id}, chapter_id={self.chapter_id}, difficulty={self.difficulty})>"