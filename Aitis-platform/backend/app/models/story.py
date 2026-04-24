from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.database import Base


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    jira_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, nullable=False)  # stored as JSON string
    framework = Column(String, nullable=False, default="Playwright")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())