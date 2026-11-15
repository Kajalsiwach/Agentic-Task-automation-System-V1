from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

PriorityType = Literal["Critical", "High", "Medium", "Low", "Very Low"]

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Title of the task")
    description: Optional[str] = Field(default="", max_length=1000)
    priority: PriorityType = Field(default="Medium")
    deadline: Optional[str] = Field(default=None)
    category: str = Field(default="General", max_length=100)
    status: Literal["Pending", "Completed"] = Field(default="Pending")

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="")
    priority: Optional[PriorityType] = Field(default="Medium")
    deadline: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default="General")
    status: Optional[Literal["Pending", "Completed"]] = Field(default="Pending")

    @field_validator("title")
    @classmethod
    def validate_title_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty.")
        return v.strip()

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Optional[PriorityType] = None
    deadline: Optional[str] = None
    category: Optional[str] = None
    status: Optional[Literal["Pending", "Completed"]] = None
    completed_at: Optional[datetime] = None

class TaskRead(TaskBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TaskFilter(BaseModel):
    status: Optional[Literal["Pending", "Completed"]] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    search: Optional[str] = None
