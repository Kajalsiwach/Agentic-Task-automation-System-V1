import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.database.session import Base
from backend.app.agents.agent import TaskForgeAgent

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_full_conversational_workflow():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Turn 1: Create a task
    r1 = agent.execute_command("Create a task to learn FastAPI with medium priority in backend category tomorrow", db=db)
    assert r1.success is True
    assert r1.intent == "CREATE_TASK"
    assert r1.data["id"] == 1
    assert r1.data["priority"] == "Medium"
    assert r1.data["category"] == "Backend"

    # Turn 2: Show all tasks
    r2 = agent.execute_command("Show all my tasks", db=db)
    assert r2.success is True
    assert r2.intent == "GET_TASKS"
    assert len(r2.data) >= 1

    # Turn 3: Show task 1
    r3 = agent.execute_command("Show task 1", db=db)
    assert r3.success is True
    assert r3.intent == "GET_TASK"
    assert r3.data["id"] == 1

    # Turn 4: Contextual update ("its" -> task 1)
    r4 = agent.execute_command("Update its priority to low", db=db)
    assert r4.success is True
    assert r4.intent == "UPDATE_TASK"
    assert r4.data["id"] == 1
    assert r4.data["priority"] == "Low"

    # Turn 5: Contextual update category
    r5 = agent.execute_command("Change its category to study", db=db)
    assert r5.success is True
    assert r5.intent == "UPDATE_TASK"
    assert r5.data["id"] == 1
    assert r5.data["category"] == "Study"

    # Turn 6: Contextual delete ("it" -> task 1)
    r6 = agent.execute_command("Delete it", db=db)
    assert r6.success is True
    assert r6.intent == "DELETE_TASK"

    # Verify task 1 is deleted
    r7 = agent.execute_command("Show task 1", db=db)
    assert r7.success is False
    assert r7.error_type == "TASK_NOT_FOUND"

    db.close()

def test_ordinal_conversational_flow():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Create two tasks
    agent.execute_command("Add a high priority task to revise Python tomorrow", db=db)
    agent.execute_command("Create a backend project called AI Task Manager", db=db)

    # Show the first task
    r_first = agent.execute_command("Show the first task", db=db)
    assert r_first.success is True
    assert r_first.data["id"] == 1

    # Update its priority to low
    r_up = agent.execute_command("Update its priority to low", db=db)
    assert r_up.success is True
    assert r_up.data["id"] == 1
    assert r_up.data["priority"] == "Low"

    # Show the previous task
    r_prev = agent.execute_command("Show the previous task", db=db)
    assert r_prev.success is True
    assert r_prev.data["id"] == 1

    db.close()

def test_safe_errors_and_out_of_distribution():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Non-existent task delete fails safely without silent deletion
    r_err = agent.execute_command("delete task 9999", db=db)
    assert r_err.success is False
    assert r_err.error_type == "TASK_NOT_FOUND"

    # Out of distribution / unknown intent
    r_unk = agent.execute_command("What is quantum computing?", db=db)
    assert r_unk.success is False
    assert r_unk.error_type == "UNKNOWN_INTENT"

    db.close()
