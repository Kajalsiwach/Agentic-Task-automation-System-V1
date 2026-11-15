import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.database.session import Base
from backend.app.agents.agent import TaskForgeAgent
from backend.app.services.task_service import TaskService
from backend.app.schemas.task import TaskCreate
from backend.app.services.intent_guardrail import IntentGuardrail
from backend.app.models.task import Task

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

# Scenario 1: TF-IDF returns UNKNOWN on "mark it as completed" -> guardrail resolves UPDATE_TASK
def test_01_guardrail_resolves_unknown_on_mark_it_as_completed():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Seed task and set active context
    t1 = TaskService.create_task(db, TaskCreate(title="Important Presentation", status="Pending"))
    agent.memory.set_active_task(t1.id, t1.title)

    # Simulate ML model returning UNKNOWN for follow-up
    with patch.object(agent.ai_pipeline, "process", return_value={"intent": "UNKNOWN", "confidence": 0.1, "entities": {}}):
        res = agent.execute_command("mark it as completed", db=db)

    assert res.success is True
    assert res.intent == "UPDATE_TASK"

    # Verify actual database state updated
    db.expire_all()
    t1_db = TaskService.get_task_by_id(db, t1.id)
    assert t1_db.status == "Completed"
    db.close()

# Scenario 2: TF-IDF misclassifies "delete that task" -> guardrail resolves DELETE_TASK
def test_02_guardrail_corrects_misclassified_delete_that_task():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Keep this task"))
    t2 = TaskService.create_task(db, TaskCreate(title="Delete this task"))
    agent.memory.set_active_task(t2.id, t2.title)

    # Simulate ML model misclassifying "delete that task" as GET_TASK
    with patch.object(agent.ai_pipeline, "process", return_value={"intent": "GET_TASK", "confidence": 0.45, "entities": {}}):
        res = agent.execute_command("delete that task", db=db)

    assert res.success is True
    assert res.intent == "DELETE_TASK"

    # Verify ONLY task 2 is deleted; task 1 is intact
    db.expire_all()
    all_tasks = TaskService.get_tasks(db)
    assert len(all_tasks) == 1
    assert all_tasks[0].id == t1.id
    db.close()

# Scenario 3: TF-IDF misclassifies "list all tasks" as DELETE_ALL_TASKS -> guardrail corrects to GET_TASKS
def test_03_guardrail_corrects_list_all_tasks_from_delete_all():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    TaskService.create_task(db, TaskCreate(title="Task Alpha"))
    TaskService.create_task(db, TaskCreate(title="Task Beta"))
    assert len(TaskService.get_tasks(db)) == 2

    # Simulate dangerous misclassification of "list all tasks" as DELETE_ALL_TASKS
    with patch.object(agent.ai_pipeline, "process", return_value={"intent": "DELETE_ALL_TASKS", "confidence": 0.95, "entities": {}}):
        res = agent.execute_command("list all tasks", db=db)

    assert res.success is True
    assert res.intent == "GET_TASKS"

    # Verify 0 tasks were deleted
    db.expire_all()
    assert len(TaskService.get_tasks(db)) == 2
    db.close()

# Scenario 4: TF-IDF misclassifies "delete all tasks" as GET_TASKS -> guardrail corrects to DELETE_ALL_TASKS
def test_04_guardrail_corrects_delete_all_tasks_and_triggers_confirmation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    TaskService.create_task(db, TaskCreate(title="Task 1"))
    TaskService.create_task(db, TaskCreate(title="Task 2"))

    # Simulate misclassification of "delete all tasks" as GET_TASKS
    with patch.object(agent.ai_pipeline, "process", return_value={"intent": "GET_TASKS", "confidence": 0.88, "entities": {}}):
        res = agent.execute_command("delete all tasks", db=db, confirmed=False)

    # Guardrail must force DELETE_ALL_TASKS, triggering Stage 1 confirmation requirement
    assert res.success is False
    assert res.intent == "DELETE_ALL_TASKS"
    assert res.error_type == "CONFIRMATION_REQUIRED"

    # Verify tasks remain untouched in DB
    db.expire_all()
    assert len(TaskService.get_tasks(db)) == 2
    db.close()

# Scenario 5: TF-IDF returns UNKNOWN on 'rename task 1 to "Final version"' -> guardrail resolves UPDATE_TASK
def test_05_guardrail_resolves_unknown_rename_command():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Draft version"))

    # Simulate ML model returning UNKNOWN for rename
    with patch.object(agent.ai_pipeline, "process", return_value={"intent": "UNKNOWN", "confidence": 0.0, "entities": {}}):
        res = agent.execute_command(f'rename task {t1.id} to "Final version"', db=db)

    assert res.success is True
    assert res.intent == "UPDATE_TASK"

    # Verify title renamed in DB
    db.expire_all()
    t1_db = TaskService.get_task_by_id(db, t1.id)
    assert t1_db.title == "Final version"
    db.close()

# Scenario 6: Non-template natural phrasing passes through TF-IDF model unchanged
def test_06_non_template_natural_phrasing_passes_through():
    # Direct guardrail test
    intent, conf = IntentGuardrail.resolve_intent(
        raw_text="What do I need to do today?",
        predicted_intent="GET_TASKS",
        confidence=0.78,
        has_active_context=False,
    )
    assert intent == "GET_TASKS"
    assert conf == 0.78

    intent2, conf2 = IntentGuardrail.resolve_intent(
        raw_text="Random conversation about clouds",
        predicted_intent="UNKNOWN",
        confidence=0.05,
        has_active_context=False,
    )
    assert intent2 == "UNKNOWN"
    assert conf2 == 0.05

# Scenario 7: CREATE_TASK post-execution DB verification confirms row in SQLite
def test_07_create_task_post_execution_db_verification():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    res = agent.execute_command("Create a task called 'Deploy backend service' with high priority in DevOps category", db=db)
    assert res.success is True
    assert res.intent == "CREATE_TASK"

    # Direct SQLite query verifying exact persistence
    db.expire_all()
    task_row = db.query(Task).filter(Task.id == res.data["id"]).first()
    assert task_row is not None
    assert task_row.title == "Deploy backend service"
    assert task_row.priority == "High"
    assert task_row.category == "DevOps"
    assert task_row.status == "Pending"
    db.close()

# Scenario 8: UPDATE_TASK post-execution DB verification confirms updated fields in SQLite
def test_08_update_task_post_execution_db_verification():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Initial Title", priority="Low", status="Pending"))

    res = agent.execute_command(f"Update task {t1.id} priority to High and status to Completed", db=db)
    assert res.success is True
    assert res.intent == "UPDATE_TASK"

    # Direct SQLite query verifying persistence
    db.expire_all()
    task_row = db.query(Task).filter(Task.id == t1.id).first()
    assert task_row is not None
    assert task_row.priority == "High"
    assert task_row.status == "Completed"
    assert task_row.completed_at is not None
    db.close()

# Scenario 9: DELETE_TASK post-execution DB verification confirms row no longer exists in SQLite
def test_09_delete_task_post_execution_db_verification():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Task to Delete"))
    t1_id = t1.id

    res = agent.execute_command(f"Delete task {t1_id}", db=db)
    assert res.success is True
    assert res.intent == "DELETE_TASK"

    # Direct SQLite verification
    db.expire_all()
    deleted_row = db.query(Task).filter(Task.id == t1_id).first()
    assert deleted_row is None
    db.close()

# Scenario 10: Simulated persistence failure triggers EXECUTION_VERIFICATION_FAILED
def test_10_simulated_persistence_failure_triggers_execution_verification_failed():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Database Failure Test Task", priority="Low"))
    t1_id = t1.id

    # Simulate a bug/failure where TaskService returns an updated dict but does NOT commit to SQLite
    original_update = TaskService.update_task
    def mock_no_op_update(session, task_id, update_data):
        # Read task without persisting requested priority changes
        task = session.query(Task).filter(Task.id == task_id).first()
        # Pretend it updated to "High" but leave DB row with "Low"
        return task

    with patch.object(TaskService, "update_task", side_effect=mock_no_op_update):
        res = agent.execute_command(f"Update task {t1_id} priority to High", db=db)

    # Verification must catch the discrepancy and return failure
    assert res.success is False
    assert res.error_type == "EXECUTION_VERIFICATION_FAILED"
    assert "verification failed" in res.message.lower()

    # DB record was never modified
    db.expire_all()
    t1_db = TaskService.get_task_by_id(db, t1_id)
    assert t1_db.priority == "Low"
    db.close()
