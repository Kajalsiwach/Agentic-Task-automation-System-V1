from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..schemas.task import TaskCreate, TaskUpdate, TaskRead, TaskFilter
from ..schemas.agent import AgentCommandRequest, AgentResponse, ContextState
from ..schemas.analytics import (
    AnalyticsOverviewResponse,
    CompletionTrendPoint,
    StatusDistributionData,
    PriorityDistributionPoint,
    CategoryDistributionPoint,
)
from ..services.task_service import TaskService
from ..services.analytics_service import AnalyticsService
from ..agents.agent import TaskForgeAgent
from ..core.errors import TaskNotFoundError, TaskForgeError

router = APIRouter()
agent_instance = TaskForgeAgent()

# ----------------- Health Check Endpoint -----------------

@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "TaskForge", "service": "healthy"}

# ----------------- Task CRUD Endpoints -----------------

@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task directly via REST."""
    task = TaskService.create_task(db, task_in)
    return task

@router.get("/tasks", response_model=List[TaskRead])
def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve all tasks with optional filtering."""
    filter_params = TaskFilter(
        status=status,
        priority=priority,
        category=category,
        search=search
    )
    return TaskService.get_tasks(db, filter_params)

@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Retrieve a single task by ID."""
    try:
        return TaskService.get_task_by_id(db, task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task by ID."""
    try:
        return TaskService.update_task(db, task_id, task_update)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task by ID."""
    try:
        TaskService.delete_task(db, task_id)
        return {"success": True, "message": f"Task {task_id} deleted successfully.", "deleted_id": task_id}
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

@router.delete("/tasks")
def delete_all_tasks(db: Session = Depends(get_db)):
    """Delete all tasks from the database."""
    count = TaskService.delete_all_tasks(db)
    return {"success": True, "message": f"All {count} tasks deleted successfully.", "deleted_count": count}

# ----------------- AI Agent Execution Endpoints -----------------

@router.post("/agent/execute", response_model=AgentResponse)
def execute_agent_command(cmd: AgentCommandRequest, db: Session = Depends(get_db)):
    """
    Execute natural language task command through the TaskForge AI Agent pipeline:
    Intent -> NER -> Normalizer -> Context Memory -> Planner -> Executor -> Database -> Response
    """
    return agent_instance.execute_command(goal=cmd.goal, db=db, confirmed=cmd.confirmed or False)

@router.get("/agent/context")
def get_agent_context():
    """Inspect current conversational context memory state."""
    return agent_instance.get_context_state()

@router.post("/agent/context/reset")
def reset_agent_context():
    """Reset conversational context memory."""
    agent_instance.reset_context()
    return {"success": True, "message": "Conversational context memory reset."}

# ----------------- Dashboard Metrics Endpoint -----------------

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get high-level dashboard metrics."""
    all_tasks = TaskService.get_tasks(db)
    total = len(all_tasks)
    pending = sum(1 for t in all_tasks if t.status == "Pending")
    completed = sum(1 for t in all_tasks if t.status == "Completed")
    high_priority = sum(1 for t in all_tasks if t.priority == "High")
    
    categories = {}
    for t in all_tasks:
        cat = t.category or "General"
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "high_priority": high_priority,
        "categories": categories,
    }

# ----------------- Analytics & Productivity Endpoints -----------------

@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(range: str = "7d", db: Session = Depends(get_db)):
    """Retrieve full analytics overview with all 4 chart datasets for selected date range."""
    return AnalyticsService.get_overview(db, range_str=range)

@router.get("/analytics/completion-trend", response_model=List[CompletionTrendPoint])
def get_analytics_completion_trend(range: str = "7d", db: Session = Depends(get_db)):
    """Retrieve daily task completion trend (Chart 1)."""
    return AnalyticsService.get_completion_trend(db, range_str=range)

@router.get("/analytics/status-distribution", response_model=StatusDistributionData)
def get_analytics_status_distribution(range: str = "7d", db: Session = Depends(get_db)):
    """Retrieve status distribution with separate overdue task count (Chart 2)."""
    return AnalyticsService.get_status_distribution(db, range_str=range)

@router.get("/analytics/priority-distribution", response_model=List[PriorityDistributionPoint])
def get_analytics_priority_distribution(range: str = "7d", db: Session = Depends(get_db)):
    """Retrieve priority distribution across all 5 tiers (Chart 3)."""
    return AnalyticsService.get_priority_distribution(db, range_str=range)

@router.get("/analytics/category-distribution", response_model=List[CategoryDistributionPoint])
def get_analytics_category_distribution(range: str = "7d", db: Session = Depends(get_db)):
    """Retrieve dynamic category-wise task distribution (Chart 4)."""
    return AnalyticsService.get_category_distribution(db, range_str=range)
