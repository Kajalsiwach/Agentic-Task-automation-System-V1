import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.database.session import Base
from backend.app.services.task_service import TaskService
from backend.app.schemas.task import TaskCreate
from backend.app.schemas.request_contract import (
    StructuredRequest,
    RequestFilters,
    build_structured_request,
)
from backend.app.services.request_validator import RequestValidator
from backend.app.agents.agent import TaskForgeAgent

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.query(Base.metadata.tables["tasks"]).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(Base.metadata.tables["tasks"]).delete()
        db.commit()
    finally:
        db.close()

# Scenario 1: Valid task creation passes validation
def test_01_valid_task_creation_passes_validation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # 1. Direct contract validation check
    req = StructuredRequest(
        intent="CREATE_TASK",
        confidence=0.98,
        raw_query="Create task Study Algorithms with high priority in AI category",
        task_title="Study Algorithms",
        priority="High",
        category="AI",
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is True
    assert len(validated.validation_errors) == 0

    # 2. End-to-end agent pipeline execution
    res = agent.execute_command(
        "Create a task called 'Complete Stage 1 Validation' with high priority in the Backend category.",
        db=db
    )
    assert res.success is True
    assert res.intent == "CREATE_TASK"
    assert res.data["title"] == "Complete Stage 1 Validation"
    assert res.data["priority"] == "High"
    assert res.data["category"] == "Backend"

    # Verify persisted in database
    task = TaskService.get_task_by_id(db, res.data["id"])
    assert task is not None
    assert task.title == "Complete Stage 1 Validation"
    db.close()

# Scenario 2: Creation with missing required fields fails validation
def test_02_creation_missing_required_fields_fails_validation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # 1. Direct contract validation check with empty title
    req = StructuredRequest(
        intent="CREATE_TASK",
        confidence=0.95,
        raw_query="Create a task with high priority",
        task_title=None,
        priority="High",
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is False
    assert "title" in validated.missing_fields
    assert validated.error_type == "MISSING_ENTITY"
    assert "Task title is required" in validated.validation_errors[0]

    # 2. Agent invocation with empty command
    res = agent.execute_command("", db=db)
    assert res.success is False
    assert res.error_type == "EMPTY_INPUT"
    db.close()

# Scenario 3: Update with valid task_id succeeds
def test_03_update_with_valid_task_id_succeeds():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Seed task
    task = TaskService.create_task(db, TaskCreate(title="Original Task", priority="Low", category="General"))
    task_id = task.id

    # 1. Direct contract validation
    req = StructuredRequest(
        intent="UPDATE_TASK",
        confidence=0.95,
        task_id=task_id,
        priority="High",
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is True
    assert validated.error_type is None

    # 2. End-to-end agent execution
    res = agent.execute_command(f"Update task {task_id} priority to High", db=db)
    assert res.success is True
    assert res.intent == "UPDATE_TASK"
    updated = TaskService.get_task_by_id(db, task_id)
    assert updated.priority == "High"
    db.close()

# Scenario 4: Update without fields fails validation
def test_04_update_without_fields_fails_validation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    task = TaskService.create_task(db, TaskCreate(title="Task to Update", priority="Medium"))
    task_id = task.id

    # Direct contract validation with no update fields
    req = StructuredRequest(
        intent="UPDATE_TASK",
        confidence=0.95,
        task_id=task_id,
        task_title=None,
        description=None,
        priority=None,
        category=None,
        deadline=None,
        status=None,
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is False
    assert validated.error_type == "INVALID_UPDATE"
    assert "No fields to update" in validated.validation_errors[0]

    # Agent execution without field specifications
    res = agent.execute_command(f"Update task {task_id}", db=db)
    assert res.success is False
    assert res.error_type in ("INVALID_UPDATE", "UNKNOWN_INTENT")
    db.close()

# Scenario 5: Retrieval by title resolves correctly
def test_05_retrieval_by_title_resolves_correctly():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Seed unique task
    seeded_task = TaskService.create_task(
        db,
        TaskCreate(title="Master Computer Vision", priority="High", category="AI")
    )

    # 1. Direct contract validation resolves task_id from unique title
    req = StructuredRequest(
        intent="GET_TASK",
        confidence=0.90,
        task_title="Master Computer Vision",
        task_id=None,
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is True
    assert validated.task_id == seeded_task.id

    # 2. End-to-end agent execution
    res = agent.execute_command("Show task Master Computer Vision", db=db)
    assert res.success is True
    assert res.intent == "GET_TASK"
    assert res.data["id"] == seeded_task.id
    assert res.data["title"] == "Master Computer Vision"
    db.close()

# Scenario 6: Retrieval with unknown title fails with TASK_NOT_FOUND
def test_06_retrieval_with_unknown_title_fails_task_not_found():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Direct contract validation for missing title
    req = StructuredRequest(
        intent="GET_TASK",
        confidence=0.90,
        task_title="Ghost Task Does Not Exist",
        task_id=None,
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is False
    assert validated.error_type == "TASK_NOT_FOUND"
    assert "No task found matching title" in validated.validation_errors[0]

    # Agent execution for missing title
    res = agent.execute_command("Show task Ghost Task Does Not Exist", db=db)
    assert res.success is False
    assert res.error_type == "TASK_NOT_FOUND"
    db.close()

# Scenario 7: Retrieval with multiple filters succeeds
def test_07_retrieval_with_multiple_filters_succeeds():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Seed 4 tasks
    TaskService.create_task(db, TaskCreate(title="Task A", priority="High", category="DevOps", status="Pending"))
    TaskService.create_task(db, TaskCreate(title="Task B", priority="Low", category="DevOps", status="Pending"))
    TaskService.create_task(db, TaskCreate(title="Task C", priority="High", category="DevOps", status="Completed"))
    TaskService.create_task(db, TaskCreate(title="Task D", priority="High", category="AI", status="Pending"))

    # Direct contract validation
    filters = RequestFilters(priority="High", category="DevOps", status="Pending")
    req = StructuredRequest(
        intent="GET_TASKS",
        confidence=0.95,
        filters=filters,
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is True
    assert validated.filters.priority == "High"
    assert validated.filters.category == "DevOps"
    assert validated.filters.status == "Pending"

    # Agent execution with multiple filters
    res = agent.execute_command("Show all high priority pending tasks in DevOps category", db=db)
    assert res.success is True
    assert res.intent == "GET_TASKS"
    assert len(res.data) == 1
    assert res.data[0]["title"] == "Task A"
    db.close()

# Scenario 8: Invalid task_id fails validation
def test_08_invalid_task_id_fails_validation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Non-existent ID 99999
    req_update = StructuredRequest(
        intent="UPDATE_TASK",
        confidence=0.95,
        task_id=99999,
        priority="High",
    )
    validated_up = RequestValidator.validate(req_update, db=db)
    assert validated_up.is_valid is False
    assert validated_up.error_type == "TASK_NOT_FOUND"

    req_delete = StructuredRequest(
        intent="DELETE_TASK",
        confidence=0.95,
        task_id=99999,
    )
    validated_del = RequestValidator.validate(req_delete, db=db)
    assert validated_del.is_valid is False
    assert validated_del.error_type == "TASK_NOT_FOUND"

    # Agent execution check
    res = agent.execute_command("delete task 99999", db=db)
    assert res.success is False
    assert res.error_type == "TASK_NOT_FOUND"
    db.close()

# Scenario 9: Unknown intent fails validation
def test_09_unknown_intent_fails_validation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Direct contract validation with unknown intent / low confidence
    req = StructuredRequest(
        intent="UNKNOWN",
        confidence=0.10,
        raw_query="What is the weather today?",
    )
    validated = RequestValidator.validate(req, db=db)
    assert validated.is_valid is False
    assert validated.error_type == "UNKNOWN_INTENT"
    assert "could not determine" in validated.validation_errors[0]

    # Agent execution with out-of-distribution input
    res = agent.execute_command("Tell me a bedtime story about dragons", db=db)
    assert res.success is False
    assert res.error_type == "UNKNOWN_INTENT"
    db.close()

# Scenario 10: Bulk deletion without confirmation is prevented, confirmed succeeds
def test_10_bulk_deletion_without_confirmation_prevented():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Seed 3 tasks
    TaskService.create_task(db, TaskCreate(title="Task 1"))
    TaskService.create_task(db, TaskCreate(title="Task 2"))
    TaskService.create_task(db, TaskCreate(title="Task 3"))
    assert len(TaskService.get_tasks(db)) == 3

    # 1. Unconfirmed bulk deletion attempt
    res_unconfirmed = agent.execute_command("Delete all tasks.", db=db, confirmed=False)
    assert res_unconfirmed.success is False
    assert res_unconfirmed.error_type == "CONFIRMATION_REQUIRED"
    assert res_unconfirmed.data["requires_confirmation"] is True
    assert "confirmation" in res_unconfirmed.message.lower()

    # Crucial: Verify NO tasks were deleted from the database
    tasks_after_blocked = TaskService.get_tasks(db)
    assert len(tasks_after_blocked) == 3

    # 2. Multi-turn confirmation: User replies "Yes, confirm delete all"
    res_confirmed = agent.execute_command("Yes, confirm", db=db)
    assert res_confirmed.success is True
    assert res_confirmed.intent == "DELETE_ALL_TASKS"
    assert "deleted successfully" in res_confirmed.message.lower()

    # Verify database is now empty
    assert len(TaskService.get_tasks(db)) == 0
    db.close()
