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
from backend.app.agents.agent import TaskForgeAgent
from backend.app.services.task_service import TaskService
from backend.app.schemas.task import TaskCreate

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

def test_failure_a_natural_language_title_extractions():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # 1. Quoted title + category
    r1 = agent.execute_command(
        "Create a medium priority task called 'Study Computer Vision' in the AI category.",
        db=db
    )
    assert r1.success is True
    assert r1.intent == "CREATE_TASK"
    task1 = TaskService.get_task_by_id(db, r1.data["id"])
    assert task1.title == "Study Computer Vision"
    assert task1.priority == "Medium"
    assert task1.category == "AI"

    # 2. Multi-word verb title
    r2 = agent.execute_command(
        "Create a task to study Deep Learning with medium priority.",
        db=db
    )
    assert r2.success is True
    task2 = TaskService.get_task_by_id(db, r2.data["id"])
    assert task2.title == "study Deep Learning"
    assert task2.priority == "Medium"

    # 3. Multi-word title + category
    r3 = agent.execute_command(
        "Create a task to learn Machine Learning with high priority in the AI category.",
        db=db
    )
    assert r3.success is True
    task3 = TaskService.get_task_by_id(db, r3.data["id"])
    assert task3.title == "learn Machine Learning"
    assert task3.priority == "High"
    assert task3.category == "AI"

    # 4. Quoted title without extra words
    r4 = agent.execute_command(
        "Create a task called 'Prepare ML presentation'.",
        db=db
    )
    assert r4.success is True
    task4 = TaskService.get_task_by_id(db, r4.data["id"])
    assert task4.title == "Prepare ML presentation"

    db.close()

def test_failure_b_category_extractions():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Test Task 14", category="General", priority="Medium"))
    t1_id = t1.id

    # Update category on explicit ID
    r1 = agent.execute_command(f"Update task {t1_id} category to Project.", db=db)
    assert r1.success is True
    task1 = TaskService.get_task_by_id(db, t1_id)
    assert task1.category == "Project"

    # Contextual category update ("its")
    r2 = agent.execute_command("Update its category to AI.", db=db)
    assert r2.success is True
    task2 = TaskService.get_task_by_id(db, t1_id)
    assert task2.category == "AI"

    db.close()

def test_failure_c_multiple_entity_update():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t = TaskService.create_task(db, TaskCreate(title="Multi Update Task", category="General", priority="Low"))
    t_id = t.id

    # Update both priority and category in a single command
    r = agent.execute_command(f"Update task {t_id} priority to High and category to Project.", db=db)
    assert r.success is True
    assert r.intent == "UPDATE_TASK"
    
    # Verify BOTH fields updated in the real database
    updated_task = TaskService.get_task_by_id(db, t_id)
    assert updated_task.priority == "High"
    assert updated_task.category == "Project"
    assert updated_task.title == "Multi Update Task"  # Unmodified fields stay intact

    db.close()

def test_failure_d_delete_all_tasks():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Create 3 tasks
    TaskService.create_task(db, TaskCreate(title="Task 1"))
    TaskService.create_task(db, TaskCreate(title="Task 2"))
    TaskService.create_task(db, TaskCreate(title="Task 3"))
    assert len(TaskService.get_tasks(db)) == 3

    # Delete all tasks
    r = agent.execute_command("Delete all tasks.", db=db)
    assert r.success is True
    assert r.intent == "DELETE_ALL_TASKS"
    assert "deleted successfully" in r.message.lower()

    # Verify real DB is empty
    assert len(TaskService.get_tasks(db)) == 0

    db.close()

def test_failure_f_update_after_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Create a task and show it
    r_create = agent.execute_command("Create a task to learn FastAPI with high priority", db=db)
    task_id = r_create.data["id"]

    # Delete it
    r_del = agent.execute_command("Delete it", db=db)
    assert r_del.success is True

    # Try updating its priority after deletion
    r_up = agent.execute_command("Update its priority to Low", db=db)
    # Must fail safely without crashing or corrupting DB
    assert r_up.success is False

    db.close()

def test_ordinal_operations():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Create 2 tasks
    TaskService.create_task(db, TaskCreate(title="First One", priority="Low"))
    TaskService.create_task(db, TaskCreate(title="Second One", priority="High"))

    # Show the first task & update its priority to Medium
    r1 = agent.execute_command("Show the first task.", db=db)
    assert r1.success is True
    first_id = r1.data["id"]

    r2 = agent.execute_command("Update the first task priority to Medium.", db=db)
    assert r2.success is True
    assert TaskService.get_task_by_id(db, first_id).priority == "Medium"

    # Show the last task & update its priority to Low
    r3 = agent.execute_command("Show the last task.", db=db)
    assert r3.success is True
    last_id = r3.data["id"]

    r4 = agent.execute_command("Update the last task's priority to Low.", db=db)
    assert r4.success is True
    assert TaskService.get_task_by_id(db, last_id).priority == "Low"

    db.close()
