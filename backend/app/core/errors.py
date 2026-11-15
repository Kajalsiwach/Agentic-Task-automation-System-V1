class TaskForgeError(Exception):
    """Base exception for all TaskForge domain errors."""
    def __init__(self, message: str, error_type: str = "ERROR"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type

class TaskNotFoundError(TaskForgeError):
    def __init__(self, task_id: int):
        super().__init__(f"Task with ID {task_id} was not found.", error_type="TASK_NOT_FOUND")
        self.task_id = task_id

class InvalidTaskIdError(TaskForgeError):
    def __init__(self, raw_id: str):
        super().__init__(f"Invalid task ID specified: '{raw_id}'.", error_type="INVALID_TASK_ID")

class MissingEntityError(TaskForgeError):
    def __init__(self, entity_name: str, reason: str = ""):
        msg = f"Missing required entity '{entity_name}'."
        if reason:
            msg += f" {reason}"
        super().__init__(msg, error_type="MISSING_ENTITY")
        self.entity_name = entity_name

class UnknownIntentError(TaskForgeError):
    def __init__(self, confidence: float = 0.0):
        super().__init__(
            "I could not determine your intended action. Please rephrase or specify a task command.",
            error_type="UNKNOWN_INTENT"
        )
        self.confidence = confidence

class InvalidPriorityError(TaskForgeError):
    def __init__(self, priority: str):
        super().__init__(
            f"Invalid priority '{priority}'. Supported values are: Low, Medium, High.",
            error_type="INVALID_PRIORITY"
        )

class InvalidUpdateError(TaskForgeError):
    def __init__(self, message: str):
        super().__init__(message, error_type="INVALID_UPDATE")

class InvalidPlanError(TaskForgeError):
    def __init__(self, reason: str):
        super().__init__(f"Invalid execution plan: {reason}", error_type="INVALID_PLAN")

class DatabaseError(TaskForgeError):
    def __init__(self, message: str):
        super().__init__(f"Database operation failed: {message}", error_type="DATABASE_ERROR")

class ValidationError(TaskForgeError):
    def __init__(self, message: str, error_type: str = "VALIDATION_FAILED"):
        super().__init__(message, error_type=error_type)

class ConfirmationRequiredError(TaskForgeError):
    def __init__(self, message: str = "This action requires explicit confirmation before execution."):
        super().__init__(message, error_type="CONFIRMATION_REQUIRED")

class AmbiguousConfirmationError(TaskForgeError):
    def __init__(self, message: str = "Your response was ambiguous. Please confirm with 'yes' or 'no'."):
        super().__init__(message, error_type="AMBIGUOUS_CONFIRMATION")

class AmbiguousRequestError(TaskForgeError):
    def __init__(self, message: str):
        super().__init__(message, error_type="AMBIGUOUS_REQUEST")

class AmbiguousTaskReferenceError(TaskForgeError):
    def __init__(self, message: str):
        super().__init__(message, error_type="AMBIGUOUS_TASK_REFERENCE")

class InvalidStatusError(TaskForgeError):
    def __init__(self, status: str):
        super().__init__(
            f"Invalid status '{status}'. Supported values are: Pending, Completed.",
            error_type="INVALID_STATUS"
        )

class ExecutionVerificationError(TaskForgeError):
    def __init__(self, message: str):
        super().__init__(message, error_type="EXECUTION_VERIFICATION_FAILED")
