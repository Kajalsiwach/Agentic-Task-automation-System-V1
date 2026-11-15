from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.task import Task
from ..schemas.task import TaskCreate, TaskUpdate, TaskFilter
from ..core.errors import TaskNotFoundError, DatabaseError

class TaskService:
    @staticmethod
    def create_task(db: Session, task_data: TaskCreate) -> Task:
        try:
            status_val = task_data.status or "Pending"
            completed_time = datetime.now(timezone.utc) if status_val == "Completed" else None
            task = Task(
                title=task_data.title,
                description=task_data.description or "",
                priority=task_data.priority or "Medium",
                deadline=task_data.deadline,
                category=task_data.category or "General",
                status=status_val,
                completed_at=completed_time,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Could not create task: {str(e)}")

    @staticmethod
    def get_task_by_id(db: Session, task_id: int) -> Task:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise TaskNotFoundError(task_id=task_id)
        return task

    @staticmethod
    def get_tasks(db: Session, filter_params: Optional[TaskFilter] = None) -> List[Task]:
        query = db.query(Task)
        if filter_params:
            if filter_params.status:
                query = query.filter(Task.status == filter_params.status)
            if filter_params.priority:
                query = query.filter(Task.priority == filter_params.priority)
            if filter_params.category:
                query = query.filter(Task.category.ilike(f"%{filter_params.category}%"))
            if filter_params.search:
                term = f"%{filter_params.search}%"
                query = query.filter((Task.title.ilike(term)) | (Task.description.ilike(term)))
        
        return query.order_by(Task.id.asc()).all()

    @staticmethod
    def get_task_by_ordinal(db: Session, ordinal: str) -> Optional[Task]:
        """
        Fetch task by ordinal position: 'first' or 'last'.
        """
        if ordinal == "first":
            return db.query(Task).order_by(Task.id.asc()).first()
        elif ordinal in ("last", "latest"):
            return db.query(Task).order_by(Task.id.desc()).first()
        return None

    @staticmethod
    def search_tasks_by_title(db: Session, title_query: str) -> List[Task]:
        return db.query(Task).filter(Task.title.ilike(f"%{title_query.strip()}%")).all()

    @staticmethod
    def update_task(db: Session, task_id: int, update_data: TaskUpdate) -> Task:
        task = TaskService.get_task_by_id(db, task_id)
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # Automatically manage completed_at based on status change
            if "status" in update_dict and update_dict["status"] is not None:
                new_status = update_dict["status"]
                if new_status == "Completed" and task.status != "Completed":
                    if "completed_at" not in update_dict or update_dict["completed_at"] is None:
                        task.completed_at = datetime.now(timezone.utc)
                elif new_status == "Pending":
                    task.completed_at = None

            for key, val in update_dict.items():
                if val is not None:
                    setattr(task, key, val)
            db.commit()
            db.refresh(task)
            return task
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Could not update task {task_id}: {str(e)}")

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        task = TaskService.get_task_by_id(db, task_id)
        try:
            db.delete(task)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Could not delete task {task_id}: {str(e)}")

    @staticmethod
    def delete_all_tasks(db: Session) -> int:
        try:
            count = db.query(Task).delete()
            db.commit()
            return count
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Could not delete all tasks: {str(e)}")
