import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..services.task_service import TaskService

PRONOUN_PATTERNS = [
    r"\b(it|its|that\s+task|this\s+task|the\s+task|that\s+one|this\s+one|that|this)\b",
]

PREVIOUS_TASK_PATTERNS = [
    r"\b(the\s+previous\s+task(?:'s)?|previous\s+task(?:'s)?|the\s+prior\s+task(?:'s)?|prior\s+task(?:'s)?)\b"
]

LAST_TASK_PATTERNS = [
    r"\b(the\s+last\s+task(?:'s)?|my\s+last\s+task(?:'s)?|last\s+task(?:'s)?|the\s+latest\s+task(?:'s)?|latest\s+task(?:'s)?)\b"
]

FIRST_TASK_PATTERNS = [
    r"\b(the\s+first\s+task(?:'s)?|first\s+task(?:'s)?|the\s+1st\s+task(?:'s)?|1st\s+task(?:'s)?)\b"
]

class ContextMemory:
    """
    Conversational Context Memory for multi-turn task resolution.
    Maintains active task context, turn history, and safe reference resolution.
    Does NOT implement self-improvement, model modification, or autonomous learning.
    """
    def __init__(self):
        self.last_task_id: Optional[int] = None
        self.last_task_title: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.last_tasks_cache: List[int] = []
        self.turn_history: List[Dict[str, Any]] = []
        self.pending_action: Optional[str] = None

    @property
    def last_referenced_task_id(self) -> Optional[int]:
        return self.last_task_id

    @last_referenced_task_id.setter
    def last_referenced_task_id(self, val: Optional[int]):
        self.last_task_id = val

    def set_active_task(self, task_id: Optional[int], task_title: Optional[str] = None):
        """Set or update the active task in context memory."""
        self.last_task_id = task_id
        self.last_task_title = task_title

    def clear_active_task(self):
        """Clear active task context on deletion or reset."""
        self.last_task_id = None
        self.last_task_title = None

    def record_turn(
        self,
        query: str,
        intent: str,
        task_id: Optional[int] = None,
        task_title: Optional[str] = None,
        tasks_list: Optional[List[int]] = None,
        success: bool = True,
    ):
        """Record the outcome of a conversational turn and update active task context."""
        self.last_intent = intent

        # If a task was deleted or all tasks were deleted, clear active task context immediately
        if intent in ("DELETE_TASK", "DELETE_ALL_TASKS"):
            self.clear_active_task()
        elif success and task_id is not None:
            self.set_active_task(task_id, task_title)

        if tasks_list is not None:
            self.last_tasks_cache = tasks_list

        self.turn_history.append({
            "query": query,
            "intent": intent,
            "task_id": task_id,
            "task_title": task_title,
            "success": success,
        })
        # Keep recent 20 turns
        if len(self.turn_history) > 20:
            self.turn_history = self.turn_history[-20:]

    def resolve_task_reference(
        self,
        query: str,
        raw_task_id: Optional[Any],
        db: Session,
        has_title: bool = False,
        intent: Optional[str] = None,
    ) -> Optional[int]:
        """
        Safely resolve a task reference from query, entities, or conversational memory.
        NEVER falls back to a previous task if a concrete title was provided in the query.
        Returns:
            int: Resolved task ID
            None: If reference cannot be safely determined (clarification required)
        """
        # If a concrete title was provided in the query, never resolve via context memory
        if has_title:
            return None

        # 1. If explicit integer was provided
        if isinstance(raw_task_id, int):
            return raw_task_id

        query_lower = query.lower().strip()

        # 2. Check for explicit ordinal string or pattern
        if raw_task_id in ("first", "1st") or any(re.search(p, query_lower) for p in FIRST_TASK_PATTERNS):
            first_task = TaskService.get_task_by_ordinal(db, "first")
            if first_task:
                return first_task.id
            return None

        if raw_task_id in ("last", "latest") or any(re.search(p, query_lower) for p in LAST_TASK_PATTERNS):
            last_task = TaskService.get_task_by_ordinal(db, "last")
            if last_task:
                return last_task.id
            return None

        if raw_task_id in ("previous", "prior") or any(re.search(p, query_lower) for p in PREVIOUS_TASK_PATTERNS):
            if self.last_task_id is not None:
                return self.last_task_id
            return None

        # 3. Check for pronoun reference: "it", "its", "that task", "this task", "that one", "this one", "the task"
        if any(re.search(p, query_lower) for p in PRONOUN_PATTERNS):
            if self.last_task_id is not None:
                return self.last_task_id
            return None

        # 4. Context continuation for update when no ID/title is in query (e.g. "change category to backend")
        if intent == "UPDATE_TASK" and self.last_task_id is not None:
            return self.last_task_id

        return None

    def reset(self):
        """Reset conversational context state completely."""
        self.clear_active_task()
        self.last_intent = None
        self.last_tasks_cache = []
        self.turn_history = []
        self.pending_action = None

    def get_state(self) -> Dict[str, Any]:
        return {
            "last_task_id": self.last_task_id,
            "last_task_title": self.last_task_title,
            "last_referenced_task_id": self.last_task_id,
            "last_intent": self.last_intent,
            "cached_tasks_count": len(self.last_tasks_cache),
            "turn_count": len(self.turn_history),
            "recent_history": self.turn_history[-5:],
        }
