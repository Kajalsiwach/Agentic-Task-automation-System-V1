import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.database.session import Base, get_db
from backend.main import app
from backend.app.models.task import Task
from backend.app.services.task_service import TaskService
from backend.app.schemas.task import TaskCreate, TaskUpdate

# In-memory SQLite DB
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

def test_analytics_empty_database():
    """Verify that all analytics endpoints handle an empty database gracefully."""
    res = client.get("/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_tasks"] == 0
    assert data["summary"]["completed_tasks"] == 0
    assert data["summary"]["pending_tasks"] == 0
    assert data["summary"]["overdue_tasks"] == 0
    assert data["summary"]["completion_rate"] == 0.0
    assert len(data["completion_trend"]) == 7
    assert all(pt["completed_count"] == 0 for pt in data["completion_trend"])
    assert data["status_distribution"]["total"] == 0
    assert len(data["priority_distribution"]) == 5
    assert all(p["count"] == 0 for p in data["priority_distribution"])
    assert data["category_distribution"] == []

def test_analytics_endpoints_individually():
    """Verify each individual analytics endpoint returns proper schema."""
    db = TestingSessionLocal()
    TaskService.create_task(db, TaskCreate(title="Task 1", priority="High", category="Backend", status="Pending"))
    TaskService.create_task(db, TaskCreate(title="Task 2", priority="Low", category="Frontend", status="Completed"))
    db.close()

    # 1. Completion trend
    r_trend = client.get("/analytics/completion-trend?range=7d")
    assert r_trend.status_code == 200
    trend_pts = r_trend.json()
    assert len(trend_pts) == 7
    # One task was completed today
    assert any(pt["completed_count"] == 1 for pt in trend_pts)

    # 2. Status distribution
    r_status = client.get("/analytics/status-distribution?range=7d")
    assert r_status.status_code == 200
    status_data = r_status.json()
    assert status_data["total"] == 2
    assert status_data["pending"] == 1
    assert status_data["completed"] == 1
    assert status_data["pending_percentage"] == 50.0
    assert status_data["completed_percentage"] == 50.0

    # 3. Priority distribution
    r_prio = client.get("/analytics/priority-distribution?range=7d")
    assert r_prio.status_code == 200
    prio_data = r_prio.json()
    prio_map = {p["priority"]: p["count"] for p in prio_data}
    assert prio_map["High"] == 1
    assert prio_map["Low"] == 1
    assert prio_map["Medium"] == 0

    # 4. Category distribution
    r_cat = client.get("/analytics/category-distribution?range=7d")
    assert r_cat.status_code == 200
    cat_data = r_cat.json()
    cat_map = {c["category"]: c["count"] for c in cat_data}
    assert cat_map["Backend"] == 1
    assert cat_map["Frontend"] == 1

def test_overdue_tasks_calculation():
    """Verify overdue tasks are detected and calculated separately without double counting."""
    db = TestingSessionLocal()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Overdue pending task
    TaskService.create_task(db, TaskCreate(title="Overdue Task", deadline=yesterday, status="Pending"))
    # Non-overdue pending task
    TaskService.create_task(db, TaskCreate(title="Future Task", deadline=tomorrow, status="Pending"))
    # Completed task with past deadline (NOT overdue because it's completed)
    TaskService.create_task(db, TaskCreate(title="Completed Past Task", deadline=yesterday, status="Completed"))
    db.close()

    r = client.get("/analytics/status-distribution")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["pending"] == 2
    assert data["completed"] == 1
    assert data["overdue"] == 1  # Exactly 1 task is overdue

def test_task_lifecycle_updates_analytics():
    """Verify creating, updating, completing, and deleting tasks correctly updates analytics."""
    # Step 1: Create task
    create_res = client.post("/tasks", json={
        "title": "Build Analytics",
        "priority": "Critical",
        "category": "Data",
        "status": "Pending"
    })
    assert create_res.status_code == 201
    task_id = create_res.json()["id"]

    overview1 = client.get("/analytics/overview").json()
    assert overview1["summary"]["total_tasks"] == 1
    assert overview1["summary"]["pending_tasks"] == 1
    assert overview1["summary"]["completed_tasks"] == 0

    prio1 = {p["priority"]: p["count"] for p in overview1["priority_distribution"]}
    assert prio1["Critical"] == 1

    cat1 = {c["category"]: c["count"] for c in overview1["category_distribution"]}
    assert cat1["Data"] == 1

    # Step 2: Complete the task
    patch_res = client.patch(f"/tasks/{task_id}", json={"status": "Completed"})
    assert patch_res.status_code == 200

    overview2 = client.get("/analytics/overview").json()
    assert overview2["summary"]["completed_tasks"] == 1
    assert overview2["summary"]["pending_tasks"] == 0
    assert overview2["summary"]["completion_rate"] == 100.0

    # Trend should reflect the completion today
    today_str = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    today_point = next(pt for pt in overview2["completion_trend"] if pt["date"] == today_str)
    assert today_point["completed_count"] == 1

    # Step 3: Delete task
    del_res = client.delete(f"/tasks/{task_id}")
    assert del_res.status_code == 200

    overview3 = client.get("/analytics/overview").json()
    assert overview3["summary"]["total_tasks"] == 0
    assert overview3["summary"]["completed_tasks"] == 0

def test_date_range_selector_filters():
    """Verify date ranges 7d, 30d, 90d, and all return appropriate day spans."""
    for r_code, expected_days in [("7d", 7), ("30d", 30), ("90d", 90)]:
        res = client.get(f"/analytics/overview?range={r_code}")
        assert res.status_code == 200
        data = res.json()
        assert data["date_range"]["days_count"] == expected_days
        assert len(data["completion_trend"]) == expected_days

    # "all"
    res_all = client.get("/analytics/overview?range=all")
    assert res_all.status_code == 200
    assert res_all.json()["date_range"]["range"] == "all"
