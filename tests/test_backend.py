import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.database.session import Base, get_db
from backend.main import app

from sqlalchemy.pool import StaticPool
from backend.app.models.task import Task

# In-memory SQLite database for tests with StaticPool so all connections share the same memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.query(Task).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = TestingSessionLocal()
    try:
        db.query(Task).delete()
        db.commit()
    finally:
        db.close()

def test_create_and_get_task():
    response = client.post("/tasks", json={
        "title": "Learn FastAPI",
        "description": "Study request handling and Pydantic",
        "priority": "High",
        "category": "Backend",
        "status": "Pending"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == "Learn FastAPI"
    assert data["priority"] == "High"

    task_id = data["id"]
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Learn FastAPI"

def test_get_tasks_filtering():
    client.post("/tasks", json={"title": "Task A", "priority": "High", "status": "Pending", "category": "Dev"})
    client.post("/tasks", json={"title": "Task B", "priority": "Low", "status": "Completed", "category": "Personal"})

    res_all = client.get("/tasks")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    res_pending = client.get("/tasks?status=Pending")
    assert len(res_pending.json()) == 1
    assert res_pending.json()[0]["title"] == "Task A"

    res_high = client.get("/tasks?priority=High")
    assert len(res_high.json()) == 1

def test_update_task():
    create_res = client.post("/tasks", json={"title": "Task 1", "priority": "Medium"})
    task_id = create_res.json()["id"]
    patch_res = client.patch(f"/tasks/{task_id}", json={"priority": "High", "status": "Completed"})
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["priority"] == "High"
    assert updated["status"] == "Completed"

def test_delete_task():
    create_res = client.post("/tasks", json={"title": "Task To Delete"})
    task_id = create_res.json()["id"]
    del_res = client.delete(f"/tasks/{task_id}")
    assert del_res.status_code == 200

    # Ensure it is gone
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 404

def test_invalid_task_id_fails():
    res = client.get("/tasks/9999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_empty_title_validation_fails():
    res = client.post("/tasks", json={"title": "   "})
    assert res.status_code == 422
