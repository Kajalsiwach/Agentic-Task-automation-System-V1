import re
from typing import Optional, Any
from sqlalchemy.orm import Session

from ..models.task import Task
from ..services.task_service import TaskService
from ..services.task_resolver import TaskResolver
from ..schemas.request_contract import StructuredRequest
from ..core.errors import TaskNotFoundError

ALLOWED_PRIORITIES = {"Low", "Medium", "High", "Critical", "Very Low"}
ALLOWED_STATUSES = {"Pending", "Completed"}

AFFIRMATIVE_PATTERN = re.compile(
    r"^\s*(?:"
    r"yes|yep|yeah|y|sure|ok|okay|confirm|confirmed|proceed|do\s+it|"
    r"yes\s*,?\s*(?:please|confirm|confirmed|proceed|do\s+it|sure)|"
    r"yes\s+please|"
    r"yes\s*,?\s*delete\s+all(?:\s+tasks)?|"
    r"confirm\s+delete\s+all(?:\s+tasks)?|"
    r"delete\s+all(?:\s+tasks)?\s*,?\s*confirm|"
    r"confirm\s+deletion"
    r")\s*[.!]?$",
    re.IGNORECASE
)

class RequestValidator:
    """
    Centralized, deterministic request validation layer between AI interpretation
    and task execution.
    Enforces business rules, entity existence, and prevents dangerous unconfirmed actions.
    """

    @classmethod
    def validate(
        cls,
        request: StructuredRequest,
        db: Session,
        memory: Optional[Any] = None,
        confirmed: bool = False,
    ) -> StructuredRequest:
        """
        Validate a StructuredRequest before planning and execution.
        Returns the request updated with validation status, errors, and missing fields.
        """
        # 1. Unknown or low-confidence intent
        if request.intent == "UNKNOWN" or request.confidence < 0.20:
            request.is_valid = False
            request.error_type = "UNKNOWN_INTENT"
            request.validation_errors.append(
                "I could not determine your intended action. Please rephrase or specify a task command."
            )
            return request

        # 2. Dispatch validation per intent
        if request.intent == "CREATE_TASK":
            return cls._validate_create_task(request)
        elif request.intent == "UPDATE_TASK":
            return cls._validate_update_task(request, db)
        elif request.intent == "GET_TASK":
            return cls._validate_get_task(request, db)
        elif request.intent == "GET_TASKS":
            return cls._validate_get_tasks(request)
        elif request.intent == "DELETE_TASK":
            return cls._validate_delete_task(request, db)
        elif request.intent == "DELETE_ALL_TASKS":
            return cls._validate_delete_all_tasks(request, memory=memory, confirmed=confirmed)
        else:
            request.is_valid = False
            request.error_type = "UNKNOWN_INTENT"
            request.validation_errors.append(f"Unrecognized intent '{request.intent}'.")
            return request

    @classmethod
    def _validate_create_task(cls, request: StructuredRequest) -> StructuredRequest:
        if not request.task_title or not request.task_title.strip():
            request.is_valid = False
            request.missing_fields.append("title")
            request.validation_errors.append("Task title is required to create a task.")
            request.error_type = "MISSING_ENTITY"
            return request

        if request.priority:
            if request.priority not in ALLOWED_PRIORITIES:
                request.is_valid = False
                request.error_type = "INVALID_PRIORITY"
                request.validation_errors.append(
                    f"Invalid priority '{request.priority}'. Supported values are: Low, Medium, High."
                )
                return request

        if request.status:
            if request.status not in ALLOWED_STATUSES:
                request.is_valid = False
                request.error_type = "INVALID_STATUS"
                request.validation_errors.append(
                    f"Invalid status '{request.status}'. Supported values are: Pending, Completed."
                )
                return request

        return request

    @classmethod
    def _validate_update_task(cls, request: StructuredRequest, db: Session) -> StructuredRequest:
        # Check task_id existence or resolve by title
        resolved_from_title = False
        if request.task_id is None:
            if not request.task_title or not request.task_title.strip():
                request.is_valid = False
                request.missing_fields.append("task_id")
                request.error_type = "TASK_NOT_FOUND" if request.context_reference else "MISSING_ENTITY"
                request.validation_errors.append(
                    "No active task found in context. Please specify which task ID or title you mean."
                    if request.context_reference
                    else "Please specify which task you would like to update."
                )
                return request

            res = TaskResolver.resolve(db, task_id=None, title_query=request.task_title)
            if not res.is_success:
                request.is_valid = False
                request.error_type = res.error_type
                request.validation_errors.append(res.error_message)
                return request

            request.task_id = res.task.id
            resolved_from_title = True
        else:
            res = TaskResolver.resolve(db, task_id=request.task_id, title_query=None)
            if not res.is_success:
                request.is_valid = False
                request.error_type = res.error_type
                request.validation_errors.append(res.error_message)
                return request

        # If renaming with new_title, assign new_title to task_title for the update operation
        if request.new_title:
            request.task_title = request.new_title
        elif resolved_from_title:
            # Title was used only to locate the task, not as an update value
            request.task_title = None

        # Check that at least one valid update field is provided
        update_fields = [
            request.task_title,
            request.description,
            request.priority,
            request.category,
            request.deadline,
            request.status,
        ]
        has_update = any(f is not None for f in update_fields)
        if not has_update:
            request.is_valid = False
            request.error_type = "INVALID_UPDATE"
            request.validation_errors.append("No fields to update were specified in your request.")
            return request

        # Validate priority if specified
        if request.priority and request.priority not in ALLOWED_PRIORITIES:
            request.is_valid = False
            request.error_type = "INVALID_PRIORITY"
            request.validation_errors.append(
                f"Invalid priority '{request.priority}'. Supported values are: Low, Medium, High."
            )
            return request

        # Validate status if specified
        if request.status and request.status not in ALLOWED_STATUSES:
            request.is_valid = False
            request.error_type = "INVALID_STATUS"
            request.validation_errors.append(
                f"Invalid status '{request.status}'. Supported values are: Pending, Completed."
            )
            return request

        return request

    @classmethod
    def _validate_get_task(cls, request: StructuredRequest, db: Session) -> StructuredRequest:
        if request.task_id is None and (not request.task_title or not request.task_title.strip()):
            request.is_valid = False
            request.error_type = "TASK_NOT_FOUND" if request.context_reference else "MISSING_ENTITY"
            if request.error_type == "MISSING_ENTITY":
                request.missing_fields.append("task_id")
            request.validation_errors.append(
                "No active task found in context. Please specify which task ID or title you mean."
                if request.context_reference
                else "Please specify which task ID or title you would like to view."
            )
            return request

        res = TaskResolver.resolve(db, task_id=request.task_id, title_query=request.task_title)
        if not res.is_success:
            request.is_valid = False
            request.error_type = res.error_type
            request.validation_errors.append(res.error_message)
            return request

        request.task_id = res.task.id
        return request

    @classmethod
    def _validate_get_tasks(cls, request: StructuredRequest) -> StructuredRequest:
        if request.filters:
            if request.filters.priority and request.filters.priority not in ALLOWED_PRIORITIES:
                request.is_valid = False
                request.error_type = "INVALID_PRIORITY"
                request.validation_errors.append(
                    f"Invalid priority filter '{request.filters.priority}'."
                )
                return request
            if request.filters.status and request.filters.status not in ALLOWED_STATUSES:
                request.is_valid = False
                request.error_type = "INVALID_STATUS"
                request.validation_errors.append(
                    f"Invalid status filter '{request.filters.status}'."
                )
                return request
        return request

    @classmethod
    def _validate_delete_task(cls, request: StructuredRequest, db: Session) -> StructuredRequest:
        if request.task_id is None and (not request.task_title or not request.task_title.strip()):
            request.is_valid = False
            request.error_type = "TASK_NOT_FOUND" if request.context_reference else "MISSING_ENTITY"
            if request.error_type == "MISSING_ENTITY":
                request.missing_fields.append("task_id")
            request.validation_errors.append(
                "No active task found in context. Please specify which task ID or title you would like to delete."
                if request.context_reference
                else "Please specify which task you would like to delete."
            )
            return request

        res = TaskResolver.resolve(db, task_id=request.task_id, title_query=request.task_title)
        if not res.is_success:
            request.is_valid = False
            request.error_type = res.error_type
            request.validation_errors.append(res.error_message)
            return request

        request.task_id = res.task.id
        return request

    @classmethod
    def _validate_delete_all_tasks(
        cls,
        request: StructuredRequest,
        memory: Optional[Any] = None,
        confirmed: bool = False,
    ) -> StructuredRequest:
        # Check confirmation via explicit parameter or strict affirmative pattern
        is_confirmed = confirmed
        if not is_confirmed and request.raw_query:
            if AFFIRMATIVE_PATTERN.match(request.raw_query.strip()):
                is_confirmed = True

        if not is_confirmed:
            request.requires_confirmation = True
            request.is_valid = False
            request.error_type = "CONFIRMATION_REQUIRED"
            request.validation_errors.append(
                "Deleting all tasks requires explicit confirmation. Please confirm to proceed."
            )
            return request

        request.requires_confirmation = False
        request.is_valid = True
        return request
