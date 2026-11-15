from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.task import Task

class TaskResolutionResult:
    """
    Result of a deterministic task resolution attempt.
    """
    def __init__(
        self,
        task: Optional[Task] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        candidates: Optional[List[Task]] = None,
    ):
        self.task = task
        self.error_type = error_type
        self.error_message = error_message
        self.candidates = candidates or []

    @property
    def is_success(self) -> bool:
        return self.task is not None and self.error_type is None

class TaskResolver:
    """
    Deterministic Task Resolution & Ambiguity Guard.
    Resolves tasks by explicit ID or title query strictly according to deterministic precedence:
    1. Explicit task_id lookup (exact id == task_id)
    2. Exact case-insensitive title match
    3. Partial case-insensitive substring match (minimum 3 non-whitespace characters)
    4. Clean TASK_NOT_FOUND failure (never guesses)
    Disambiguates multiple matches by returning AMBIGUOUS_TASK_REFERENCE with candidate listing.
    """

    @classmethod
    def resolve(
        cls,
        db: Session,
        task_id: Optional[int] = None,
        title_query: Optional[str] = None,
    ) -> TaskResolutionResult:
        # 1. Explicit task_id lookup
        if task_id is not None:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                return TaskResolutionResult(task=task)
            return TaskResolutionResult(
                error_type="TASK_NOT_FOUND",
                error_message=f"Task with ID {task_id} was not found."
            )

        # 2. Title lookup
        if not title_query or not title_query.strip():
            return TaskResolutionResult(
                error_type="MISSING_ENTITY",
                error_message="Please specify which task ID or title you would like to target."
            )

        q = title_query.strip()
        q_lower = q.lower()

        # Query all tasks for deterministic, case-insensitive in-memory matching
        all_tasks = db.query(Task).order_by(Task.id.asc()).all()

        # Step 1: Exact case-insensitive match
        exact_matches = [
            t for t in all_tasks
            if t.title and t.title.strip().lower() == q_lower
        ]

        if len(exact_matches) == 1:
            return TaskResolutionResult(task=exact_matches[0])
        elif len(exact_matches) > 1:
            candidates_str = ", ".join(f"ID {t.id}: '{t.title}'" for t in exact_matches)
            return TaskResolutionResult(
                error_type="AMBIGUOUS_TASK_REFERENCE",
                error_message=f"Multiple tasks found with title '{q}': [{candidates_str}]. Please specify by task ID.",
                candidates=exact_matches,
            )

        # Step 2: Substring / partial case-insensitive match (only if zero exact matches)
        # Require meaningful query length (at least 3 non-whitespace characters)
        if len(q) < 3:
            return TaskResolutionResult(
                error_type="TASK_NOT_FOUND",
                error_message=f"No task found matching title '{q}'."
            )

        partial_matches = [
            t for t in all_tasks
            if t.title and q_lower in t.title.lower()
        ]

        if len(partial_matches) == 1:
            return TaskResolutionResult(task=partial_matches[0])
        elif len(partial_matches) > 1:
            candidates_str = ", ".join(f"ID {t.id}: '{t.title}'" for t in partial_matches)
            return TaskResolutionResult(
                error_type="AMBIGUOUS_TASK_REFERENCE",
                error_message=f"Multiple tasks found matching '{q}': [{candidates_str}]. Please specify by task ID.",
                candidates=partial_matches,
            )

        # Step 3: Zero matches
        return TaskResolutionResult(
            error_type="TASK_NOT_FOUND",
            error_message=f"No task found matching title '{q}'."
        )
