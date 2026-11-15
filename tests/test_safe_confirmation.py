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

def seed_tasks(db, count=3):
    created = []
    for i in range(1, count + 1):
        t = TaskService.create_task(db, TaskCreate(title=f"Sample Task {i}", priority="Medium"))
        created.append(t)
    return created

# Test 1: DELETE_ALL without confirmation is blocked
def test_01_delete_all_without_confirmation_is_blocked():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)
    assert len(TaskService.get_tasks(db)) == 3

    res = agent.execute_command("Delete all tasks", db=db)
    assert res.success is False
    assert res.error_type == "CONFIRMATION_REQUIRED"
    assert res.data.get("requires_confirmation") is True

    # Verify actual database records are completely intact
    tasks = TaskService.get_tasks(db)
    assert len(tasks) == 3
    db.close()

# Test 2: Standalone "yes" confirms a pending deletion
def test_02_standalone_yes_confirms_pending_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False
    assert agent.memory.pending_action == "DELETE_ALL_TASKS"

    r2 = agent.execute_command("yes", db=db)
    assert r2.success is True
    assert r2.intent == "DELETE_ALL_TASKS"
    assert "deleted successfully" in r2.message.lower()

    # Verify actual database is empty
    tasks = TaskService.get_tasks(db)
    assert len(tasks) == 0
    assert agent.memory.pending_action is None
    db.close()

# Test 3: Standalone "confirm" confirms a pending deletion
def test_03_standalone_confirm_confirms_pending_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False

    r2 = agent.execute_command("confirm", db=db)
    assert r2.success is True
    assert r2.intent == "DELETE_ALL_TASKS"

    # Verify actual database is empty
    tasks = TaskService.get_tasks(db)
    assert len(tasks) == 0
    assert agent.memory.pending_action is None
    db.close()

# Test 4: "Create a task to make sure tests pass" does not authorize deletion
def test_04_create_task_make_sure_does_not_authorize_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False
    assert agent.memory.pending_action == "DELETE_ALL_TASKS"

    # Unrelated command containing "sure"
    r2 = agent.execute_command("Create a task to make sure tests pass", db=db)
    assert r2.intent == "CREATE_TASK"
    assert r2.intent != "DELETE_ALL_TASKS"

    # Verify database was NOT wiped: all 3 original tasks remain
    tasks = TaskService.get_tasks(db)
    assert len(tasks) >= 3
    # Verify pending action was cleared
    assert agent.memory.pending_action is None
    db.close()

# Test 5: "Create a task and make sure it is completed" does not authorize deletion
def test_05_create_task_make_sure_completed_does_not_authorize_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False
    assert agent.memory.pending_action == "DELETE_ALL_TASKS"

    r2 = agent.execute_command("Create a task and make sure it is completed", db=db)
    assert r2.intent != "DELETE_ALL_TASKS"

    # Original records remain untouched
    tasks = TaskService.get_tasks(db)
    assert len(tasks) >= 3
    assert agent.memory.pending_action is None
    db.close()

# Test 6: An unrelated GET command cancels pending deletion
def test_06_unrelated_get_command_cancels_pending_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False
    assert agent.memory.pending_action == "DELETE_ALL_TASKS"

    # Unrelated GET command
    r2 = agent.execute_command("Show all tasks", db=db)
    assert r2.success is True
    assert r2.intent == "GET_TASKS"
    assert len(r2.data) == 3

    # Verify database still has all 3 tasks
    assert len(TaskService.get_tasks(db)) == 3
    assert agent.memory.pending_action is None
    db.close()

# Test 7: An explicit cancellation prevents deletion
def test_07_explicit_cancellation_prevents_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False
    assert agent.memory.pending_action == "DELETE_ALL_TASKS"

    # Explicit cancel
    r2 = agent.execute_command("cancel", db=db)
    assert r2.success is True
    assert "cancelled" in r2.message.lower()

    # All 3 records remain intact
    assert len(TaskService.get_tasks(db)) == 3
    assert agent.memory.pending_action is None
    db.close()

# Test 8: An ambiguous response does not authorize deletion
def test_08_ambiguous_response_does_not_authorize_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    r1 = agent.execute_command("Delete all tasks", db=db)
    assert r1.success is False

    # Ambiguous response
    r2 = agent.execute_command("maybe later", db=db)
    assert r2.success is False
    assert r2.error_type == "AMBIGUOUS_CONFIRMATION"

    # All 3 records remain intact
    assert len(TaskService.get_tasks(db)) == 3
    db.close()

# Test 9: A consumed confirmation cannot be reused
def test_09_consumed_confirmation_cannot_be_reused():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    # First delete-all cycle
    r1 = agent.execute_command("Delete all tasks", db=db)
    r2 = agent.execute_command("yes", db=db)
    assert r2.success is True
    assert len(TaskService.get_tasks(db)) == 0
    assert agent.memory.pending_action is None

    # Seed 2 new tasks
    seed_tasks(db, count=2)
    assert len(TaskService.get_tasks(db)) == 2

    # User says "yes" again without a pending delete all
    r3 = agent.execute_command("yes", db=db)
    assert r3.intent != "DELETE_ALL_TASKS"

    # Crucial: The 2 new tasks must NOT be deleted
    assert len(TaskService.get_tasks(db)) == 2
    db.close()

# Test 10: A new DELETE_ALL request requires its own confirmation
def test_10_new_delete_all_request_requires_its_own_confirmation():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()
    seed_tasks(db, count=3)

    # Initial request + cancel
    agent.execute_command("Delete all tasks", db=db)
    agent.execute_command("cancel", db=db)
    assert len(TaskService.get_tasks(db)) == 3
    assert agent.memory.pending_action is None

    # Second independent request
    r_new = agent.execute_command("Delete all tasks", db=db)
    assert r_new.success is False
    assert r_new.error_type == "CONFIRMATION_REQUIRED"

    # Verify still not deleted
    assert len(TaskService.get_tasks(db)) == 3
    db.close()
