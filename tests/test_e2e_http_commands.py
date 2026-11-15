import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.main import app
from backend.app.database.session import Base, get_db
from backend.app.models.task import Task
from backend.app.services.task_service import TaskService
from backend.app.schemas.task import TaskCreate
from backend.app.api.endpoints import agent_instance

# Isolated in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    agent_instance.reset_context()
    db = TestingSessionLocal()
    try:
        db.query(Task).delete()
        db.commit()
    finally:
        db.close()
    yield
    agent_instance.reset_context()
    db = TestingSessionLocal()
    try:
        db.query(Task).delete()
        db.commit()
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

# Scenario 1: Create task with natural language + metadata
def test_01_http_create_task_natural_language_metadata(client):
    cmd = "Create a task to prepare sprint demo with high priority due tomorrow"
    resp = client.post("/api/agent/execute", json={"goal": cmd})
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["intent"] == "CREATE_TASK"
    assert data["data"]["priority"] == "High"
    assert data["data"]["deadline"] is not None
    created_id = data["data"]["id"]

    # Direct SQLite DB check
    db = TestingSessionLocal()
    try:
        task_row = db.query(Task).filter(Task.id == created_id).first()
        assert task_row is not None
        assert "sprint demo" in task_row.title.lower()
        assert task_row.priority == "High"
        assert task_row.deadline is not None
        assert task_row.status == "Pending"
    finally:
        db.close()

# Scenario 2 & 3: Create second/third tasks & list all tasks without deleting anything
def test_02_and_03_http_create_multiple_and_list_all_tasks(client):
    # Step 1: Create tasks
    r1 = client.post("/api/agent/execute", json={"goal": "Create a task to prepare sprint demo with high priority"})
    r2 = client.post("/api/agent/execute", json={"goal": "Add task Review Q4 report"})
    r3 = client.post("/api/agent/execute", json={"goal": "Create task Write Q3 report"})
    assert r1.status_code == 200 and r1.json()["success"] is True
    assert r2.status_code == 200 and r2.json()["success"] is True
    assert r3.status_code == 200 and r3.json()["success"] is True

    # Step 2: List all tasks
    r_list = client.post("/api/agent/execute", json={"goal": "List all tasks"})
    assert r_list.status_code == 200
    list_data = r_list.json()
    assert list_data["success"] is True
    assert list_data["intent"] == "GET_TASKS"
    assert len(list_data["data"]) == 3

    # Direct SQLite DB check: all 3 tasks remain intact
    db = TestingSessionLocal()
    try:
        count = db.query(Task).count()
        assert count == 3
    finally:
        db.close()

# Scenario 4: Follow-up pronoun update
def test_04_http_follow_up_pronoun_update(client):
    # Step 1: Create task
    r_create = client.post("/api/agent/execute", json={"goal": "Create task Submit expense report"})
    assert r_create.status_code == 200
    task_id = r_create.json()["data"]["id"]

    # Step 2: Contextual follow-up update
    r_update = client.post("/api/agent/execute", json={"goal": "Mark that task as completed"})
    assert r_update.status_code == 200
    up_data = r_update.json()
    assert up_data["success"] is True
    assert up_data["intent"] == "UPDATE_TASK"

    # Direct SQLite DB check: status is Completed
    db = TestingSessionLocal()
    try:
        task_row = db.query(Task).filter(Task.id == task_id).first()
        assert task_row is not None
        assert task_row.status == "Completed"
        assert task_row.title == "Submit expense report"
    finally:
        db.close()

# Scenario 5: Rename task by ID
def test_05_http_rename_task_by_id(client):
    db = TestingSessionLocal()
    try:
        t1 = TaskService.create_task(db, TaskCreate(title="Initial Sprint Demo", priority="Medium"))
        t1_id = t1.id
    finally:
        db.close()

    resp = client.post("/api/agent/execute", json={"goal": f'Rename task {t1_id} to "Final sprint demo"'})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["intent"] == "UPDATE_TASK"

    # Direct SQLite DB check: title is updated
    db = TestingSessionLocal()
    try:
        task_row = db.query(Task).filter(Task.id == t1_id).first()
        assert task_row is not None
        assert task_row.title == "Final sprint demo"
    finally:
        db.close()

# Scenario 6: Ambiguous delete protection
def test_06_http_ambiguous_delete_protection(client):
    db = TestingSessionLocal()
    try:
        TaskService.create_task(db, TaskCreate(title="Review Q4 report"))
        TaskService.create_task(db, TaskCreate(title="Write Q3 report"))
    finally:
        db.close()

    # Ambiguous delete command targeting substring "report"
    resp = client.post("/api/agent/execute", json={"goal": "Delete task report"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error_type"] == "AMBIGUOUS_TASK_REFERENCE"
    assert "Multiple tasks found matching 'report'" in data["message"]

    # Direct SQLite DB check: zero tasks were deleted
    db = TestingSessionLocal()
    try:
        count = db.query(Task).count()
        assert count == 2
    finally:
        db.close()

# Scenario 7: Delete specific task by exact title
def test_07_http_delete_specific_task_by_exact_title(client):
    db = TestingSessionLocal()
    try:
        t1 = TaskService.create_task(db, TaskCreate(title="Review Q4 report"))
        t2 = TaskService.create_task(db, TaskCreate(title="Write Q3 report"))
        t1_id = t1.id
        t2_id = t2.id
    finally:
        db.close()

    resp = client.post("/api/agent/execute", json={"goal": "Delete task Review Q4 report"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["intent"] == "DELETE_TASK"

    # Direct SQLite DB check: ONLY task 1 deleted, task 2 remains intact
    db = TestingSessionLocal()
    try:
        remaining = db.query(Task).all()
        assert len(remaining) == 1
        assert remaining[0].id == t2_id
        assert remaining[0].title == "Write Q3 report"
    finally:
        db.close()

# Scenario 8: Orphaned follow-up after delete
def test_08_http_orphaned_follow_up_after_delete(client):
    db = TestingSessionLocal()
    try:
        t1 = TaskService.create_task(db, TaskCreate(title="First Safe Task"))
        t2 = TaskService.create_task(db, TaskCreate(title="Second Safe Task"))
        t2_id = t2.id
    finally:
        db.close()

    # Delete task 2
    r_del = client.post("/api/agent/execute", json={"goal": f"Delete task {t2_id}"})
    assert r_del.status_code == 200
    assert r_del.json()["success"] is True

    # Immediate follow-up "Delete that task" must be rejected cleanly
    r_orphan = client.post("/api/agent/execute", json={"goal": "Delete that task"})
    assert r_orphan.status_code == 200
    assert r_orphan.json()["success"] is False

    # Direct SQLite DB check: task 1 was NOT deleted
    db = TestingSessionLocal()
    try:
        remaining = db.query(Task).all()
        assert len(remaining) == 1
        assert remaining[0].title == "First Safe Task"
    finally:
        db.close()

# Scenario 9: Bulk delete without confirmation is blocked
def test_09_http_bulk_delete_without_confirmation_blocked(client):
    db = TestingSessionLocal()
    try:
        TaskService.create_task(db, TaskCreate(title="Task A"))
        TaskService.create_task(db, TaskCreate(title="Task B"))
        TaskService.create_task(db, TaskCreate(title="Task C"))
    finally:
        db.close()

    resp = client.post("/api/agent/execute", json={"goal": "Delete all tasks"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["intent"] == "DELETE_ALL_TASKS"
    assert data["error_type"] == "CONFIRMATION_REQUIRED"

    # Direct SQLite DB check: all 3 tasks remain intact
    db = TestingSessionLocal()
    try:
        assert db.query(Task).count() == 3
    finally:
        db.close()

# Scenario 10: False confirmation protection
def test_10_http_false_confirmation_protection(client):
    db = TestingSessionLocal()
    try:
        TaskService.create_task(db, TaskCreate(title="Task 1"))
        TaskService.create_task(db, TaskCreate(title="Task 2"))
    finally:
        db.close()

    # Initiate bulk delete (pending confirmation)
    r1 = client.post("/api/agent/execute", json={"goal": "Delete all tasks"})
    assert r1.json()["error_type"] == "CONFIRMATION_REQUIRED"

    # Command containing substring "make sure" must NEVER authorize deletion
    r2 = client.post("/api/agent/execute", json={"goal": "Create a task to make sure tests pass"})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["success"] is True
    assert data2["intent"] == "CREATE_TASK"

    # Direct SQLite DB check: existing tasks remain intact, new task created
    db = TestingSessionLocal()
    try:
        all_tasks = db.query(Task).all()
        assert len(all_tasks) == 3
        titles = [t.title for t in all_tasks]
        assert any("tests pass" in t for t in titles)
    finally:
        db.close()

# Scenario 11: Explicit bulk delete confirmation
def test_11_http_explicit_bulk_delete_confirmation(client):
    db = TestingSessionLocal()
    try:
        TaskService.create_task(db, TaskCreate(title="Task 1"))
        TaskService.create_task(db, TaskCreate(title="Task 2"))
        TaskService.create_task(db, TaskCreate(title="Task 3"))
    finally:
        db.close()

    # Step 1: Request bulk delete
    r1 = client.post("/api/agent/execute", json={"goal": "Delete all tasks"})
    assert r1.json()["error_type"] == "CONFIRMATION_REQUIRED"

    # Step 2: Provide standalone affirmative confirmation "yes"
    r2 = client.post("/api/agent/execute", json={"goal": "yes"})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["success"] is True
    assert data2["intent"] == "DELETE_ALL_TASKS"
    assert "deleted successfully" in data2["message"].lower()

    # Direct SQLite DB check: database is completely empty
    db = TestingSessionLocal()
    try:
        assert db.query(Task).count() == 0
    finally:
        db.close()
