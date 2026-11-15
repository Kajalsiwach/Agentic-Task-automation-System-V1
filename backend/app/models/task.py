from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from ..database.session import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True, default="")
    priority = Column(String(50), nullable=False, default="Medium")  # Low, Medium, High
    deadline = Column(String(100), nullable=True)  # Normalized ISO date or readable deadline
    category = Column(String(100), nullable=False, default="General")
    status = Column(String(50), nullable=False, default="Pending")  # Pending, Completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True, default=None)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "deadline": self.deadline,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
