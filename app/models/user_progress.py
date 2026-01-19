"""
UserProgress model - tracks chapter completion
"""
from sqlalchemy import Column, Integer, Boolean, Text, TIMESTAMP, DECIMAL, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid


class UserProgress(Base):
    """
    User progress table - tracks chapter completion with multi-factor algorithm
    """
    __tablename__ = "user_progress"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"), nullable=False)
    time_spent = Column(Integer)  # seconds
    scroll_progress = Column(DECIMAL(4, 2))  # 0.00 to 100.00
    is_completed = Column(Boolean, default=False)
    completion_method = Column(Text)  # Algorithm details
    updated_at = Column(TIMESTAMP, server_default=text("NOW()"), onupdate=text("NOW()"))
    
    def __repr__(self):
        return f"<UserProgress(user_id={self.user_id}, chapter_id={self.chapter_id}, completed={self.is_completed})>"