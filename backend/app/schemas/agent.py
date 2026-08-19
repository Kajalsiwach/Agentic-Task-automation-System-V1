from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AgentCommandRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="Natural language task command")

class PlanStep(BaseModel):
    step_number: int
    action: str
    description: str
    target_entity: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ExecutionPlan(BaseModel):
    intent: str
    steps: List[PlanStep] = Field(default_factory=list)
    confidence: float = 0.0
    resolved_entities: Dict[str, Any] = Field(default_factory=dict)

class AgentResponse(BaseModel):
    success: bool
    message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    plan: Optional[ExecutionPlan] = None
    data: Optional[Any] = None
    error_type: Optional[str] = None

class ContextState(BaseModel):
    last_referenced_task_id: Optional[int] = None
    last_intent: Optional[str] = None
    last_query: Optional[str] = None
    turn_count: int = 0
    recent_history: List[Dict[str, Any]] = Field(default_factory=list)
