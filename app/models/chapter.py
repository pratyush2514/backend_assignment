"""
Chapter model - exact implementation of production schema
"""
from sqlalchemy import Column, String, Integer, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
import uuid


class Chapter(Base):
    """
    Chapters table - stores PDF metadata and Gemini file references
    """
    __tablename__ = "chapters"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    gemini_file_id = Column(String, unique=True, nullable=False, index=True)
    subject = Column(String(50))
    class_level = Column(Integer)
    title = Column(String(255))
    topics = Column(JSONB)  # ["quadratic_formula", "discriminant"]
    status = Column(String(20), default="indexed")
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))
    
    def __repr__(self):
        return f"<Chapter(id={self.id}, title={self.title})>"