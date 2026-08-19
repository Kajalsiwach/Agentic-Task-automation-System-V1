from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..services.task_service import TaskService
from ..schemas.task import TaskCreate, TaskUpdate, TaskFilter
from ..core.errors import TaskForgeError

class TaskTool:
    """
    Standardized Tool interface exposing task operations to the Agent Executor.
    The agent and executor interact with business operations via this tool.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        title: str,
        description: Optional[str] = "",
        priority: Optional[str] = "Medium",
        deadline: Optional[str] = None,
        category: Optional[str] = "General",
        status: Optional[str] = "Pending",
    ) -> Dict[str, Any]:
        task_create = TaskCreate(
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            category=category,
            status=status,
        )
        task = TaskService.create_task(self.db, task_create)
        return {
            "success": True,
            "operation": "CREATE_TASK",
            "task": task.to_dict(),
        }

    def get_task(self, task_id: int) -> Dict[str, Any]:
        task = TaskService.get_task_by_id(self.db, task_id)
        return {
            "success": True,
            "operation": "GET_TASK",
            "task": task.to_dict(),
        }

    def get_all_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        filter_params = TaskFilter(
            status=status,
            priority=priority,
            category=category,
            search=search,
        )
        tasks = TaskService.get_tasks(self.db, filter_params)
        return {
            "success": True,
            "operation": "GET_TASKS",
            "count": len(tasks),
            "tasks": [t.to_dict() for t in tasks],
        }

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        deadline: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        task_update = TaskUpdate(
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            category=category,
            status=status,
        )
        updated = TaskService.update_task(self.db, task_id, task_update)
        return {
            "success": True,
            "operation": "UPDATE_TASK",
            "task": updated.to_dict(),
        }

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        TaskService.delete_task(self.db, task_id)
        return {
            "success": True,
            "operation": "DELETE_TASK",
            "deleted_task_id": task_id,
        }

    def delete_all_tasks(self) -> Dict[str, Any]:
        count = TaskService.delete_all_tasks(self.db)
        return {
            "success": True,
            "operation": "DELETE_ALL_TASKS",
            "deleted_count": count,
        }
