import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..services.task_service import TaskService

PRONOUN_PATTERNS = [
    r"\b(it|its|that task|this task|that|this)\b",
]

PREVIOUS_TASK_PATTERNS = [
    r"\b(the\s+previous\s+task|previous\s+task|the\s+prior\s+task)\b"
]

LAST_TASK_PATTERNS = [
    r"\b(the\s+last\s+task|my\s+last\s+task|last\s+task|the\s+latest\s+task)\b"
]

FIRST_TASK_PATTERNS = [
    r"\b(the\s+first\s+task|first\s+task|the\s+1st\s+task)\b"
]

class ContextMemory:
    """
    Conversational Context Memory for multi-turn task resolution.
    Maintains active task context, turn history, and safe reference resolution.
    Does NOT implement self-improvement, model modification, or autonomous learning.
    """
    def __init__(self):
        self.last_referenced_task_id: Optional[int] = None
        self.last_intent: Optional[str] = None
        self.last_tasks_cache: List[int] = []
        self.turn_history: List[Dict[str, Any]] = []

    def record_turn(
        self,
        query: str,
        intent: str,
        task_id: Optional[int] = None,
        tasks_list: Optional[List[int]] = None,
        success: bool = True,
    ):
        """Record the outcome of a conversational turn."""
        self.last_intent = intent
        if task_id is not None:
            self.last_referenced_task_id = task_id
        if tasks_list is not None:
            self.last_tasks_cache = tasks_list

        self.turn_history.append({
            "query": query,
            "intent": intent,
            "task_id": task_id,
            "success": success,
        })
        # Keep recent 20 turns
        if len(self.turn_history) > 20:
            self.turn_history = self.turn_history[-20:]

    def resolve_task_reference(
        self,
        query: str,
        raw_task_id: Optional[Any],
        db: Session
    ) -> Optional[int]:
        """
        Safely resolve a task reference from query, entities, or conversational memory.
        Returns:
            int: Resolved task ID
            None: If reference cannot be safely determined (clarification required)
        """
        query_lower = query.lower().strip()

        # 1. If explicit integer was extracted from NER or query
        if isinstance(raw_task_id, int):
            return raw_task_id

        # 2. Check for explicit ordinal string
        if raw_task_id == "first" or any(re.search(p, query_lower) for p in FIRST_TASK_PATTERNS):
            first_task = TaskService.get_task_by_ordinal(db, "first")
            if first_task:
                return first_task.id
            return None

        if raw_task_id == "last" or any(re.search(p, query_lower) for p in LAST_TASK_PATTERNS):
            last_task = TaskService.get_task_by_ordinal(db, "last")
            if last_task:
                return last_task.id
            return None

        if raw_task_id == "previous" or any(re.search(p, query_lower) for p in PREVIOUS_TASK_PATTERNS):
            if self.last_referenced_task_id is not None:
                return self.last_referenced_task_id
            return None

        # 3. Check for pronoun reference: "it", "its", "that task", "this task"
        if any(re.search(p, query_lower) for p in PRONOUN_PATTERNS):
            if self.last_referenced_task_id is not None:
                return self.last_referenced_task_id
            return None

        # 4. If query doesn't specify an ID and an update/delete/get requires an ID,
        # but the query is clearly referring to current context (e.g. "change category to backend")
        if self.last_referenced_task_id is not None:
            return self.last_referenced_task_id

        return None

    def reset(self):
        """Reset conversational context state."""
        self.last_referenced_task_id = None
        self.last_intent = None
        self.last_tasks_cache = []
        self.turn_history = []

    def get_state(self) -> Dict[str, Any]:
        return {
            "last_referenced_task_id": self.last_referenced_task_id,
            "last_intent": self.last_intent,
            "cached_tasks_count": len(self.last_tasks_cache),
            "turn_count": len(self.turn_history),
            "recent_history": self.turn_history[-5:],
        }
