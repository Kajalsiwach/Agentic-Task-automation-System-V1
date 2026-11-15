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

# Scenario 1: Exact title match (case-insensitive) resolves and updates the exact intended task
def test_01_exact_title_match_case_insensitive_resolves_and_updates():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Write unit tests", priority="Low"))
    t2 = TaskService.create_task(db, TaskCreate(title="Write integration tests", priority="Low"))

    res = agent.execute_command("Update task 'write unit tests' priority to High", db=db)
    assert res.success is True
    assert res.intent == "UPDATE_TASK"

    # Verify actual DB state
    t1_db = TaskService.get_task_by_id(db, t1.id)
    t2_db = TaskService.get_task_by_id(db, t2.id)
    assert t1_db.priority == "High"
    assert t2_db.priority == "Low"
    db.close()

# Scenario 2: Deleting a task by exact title deletes ONLY that task and leaves other tasks untouched in DB
def test_02_delete_by_exact_title_deletes_only_that_task():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Task Alpha"))
    t2 = TaskService.create_task(db, TaskCreate(title="Task Beta"))
    assert len(TaskService.get_tasks(db)) == 2

    res = agent.execute_command("Delete task Task Alpha", db=db)
    assert res.success is True
    assert res.intent == "DELETE_TASK"

    # Verify actual DB state
    all_tasks = TaskService.get_tasks(db)
    assert len(all_tasks) == 1
    assert all_tasks[0].id == t2.id
    assert all_tasks[0].title == "Task Beta"
    db.close()

# Scenario 3: Unique partial title match resolves to the single matching task
def test_03_unique_partial_title_match_resolves_single_matching_task():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Buy groceries from market", priority="Low"))
    t2 = TaskService.create_task(db, TaskCreate(title="Prepare quarterly budget", priority="Low"))

    # 1. Retrieval by unique partial substring
    res_get = agent.execute_command("Show task groceries", db=db)
    assert res_get.success is True
    assert res_get.data["id"] == t1.id

    # 2. Update by unique partial substring
    res_up = agent.execute_command("Update task groceries priority to High", db=db)
    assert res_up.success is True

    # Verify actual DB state
    t1_db = TaskService.get_task_by_id(db, t1.id)
    t2_db = TaskService.get_task_by_id(db, t2.id)
    assert t1_db.priority == "High"
    assert t2_db.priority == "Low"
    db.close()

# Scenario 4: Ambiguous partial title match is BLOCKED with AMBIGUOUS_TASK_REFERENCE and both tasks intact
def test_04_ambiguous_partial_title_match_is_blocked_with_ambiguous_task_reference():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Write Q3 report"))
    t2 = TaskService.create_task(db, TaskCreate(title="Review Q4 report"))
    assert len(TaskService.get_tasks(db)) == 2

    # Attempt delete with ambiguous substring "report"
    res = agent.execute_command("Delete task report", db=db)
    assert res.success is False
    assert res.error_type == "AMBIGUOUS_TASK_REFERENCE"
    assert "Multiple tasks found matching 'report'" in res.message
    assert f"ID {t1.id}" in res.message
    assert f"ID {t2.id}" in res.message

    # Verify BOTH tasks remain completely untouched in DB
    all_tasks = TaskService.get_tasks(db)
    assert len(all_tasks) == 2
    assert {t.id for t in all_tasks} == {t1.id, t2.id}
    db.close()

# Scenario 5: Ambiguous duplicate exact title match is BLOCKED with AMBIGUOUS_TASK_REFERENCE
def test_05_ambiguous_duplicate_exact_title_match_is_blocked():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Deploy service", priority="Low"))
    t2 = TaskService.create_task(db, TaskCreate(title="Deploy service", priority="Medium"))
    assert len(TaskService.get_tasks(db)) == 2

    # Attempt deletion on duplicate exact title
    res_del = agent.execute_command("Delete task Deploy service", db=db)
    assert res_del.success is False
    assert res_del.error_type == "AMBIGUOUS_TASK_REFERENCE"
    assert "Multiple tasks found with title 'Deploy service'" in res_del.message
    assert f"ID {t1.id}" in res_del.message
    assert f"ID {t2.id}" in res_del.message

    # Verify both tasks remain in DB
    assert len(TaskService.get_tasks(db)) == 2

    # Attempt update on duplicate exact title
    res_up = agent.execute_command("Update task 'Deploy service' priority to High", db=db)
    assert res_up.success is False
    assert res_up.error_type == "AMBIGUOUS_TASK_REFERENCE"

    # Verify neither task priority was changed
    t1_db = TaskService.get_task_by_id(db, t1.id)
    t2_db = TaskService.get_task_by_id(db, t2.id)
    assert t1_db.priority == "Low"
    assert t2_db.priority == "Medium"
    db.close()

# Scenario 6: Non-existent title or ID returns TASK_NOT_FOUND with zero DB changes
def test_06_non_existent_title_or_id_returns_task_not_found():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Critical Infrastructure Task", priority="High"))
    assert len(TaskService.get_tasks(db)) == 1

    # Non-existent ID lookup/deletion
    res_id = agent.execute_command("Delete task 9999", db=db)
    assert res_id.success is False
    assert res_id.error_type == "TASK_NOT_FOUND"
    assert len(TaskService.get_tasks(db)) == 1

    # Non-existent title deletion
    res_title = agent.execute_command("Delete task GhostTaskNameThatDoesNotExist", db=db)
    assert res_title.success is False
    assert res_title.error_type == "TASK_NOT_FOUND"
    assert len(TaskService.get_tasks(db)) == 1

    # Verify the real task was never touched
    t1_db = TaskService.get_task_by_id(db, t1.id)
    assert t1_db.title == "Critical Infrastructure Task"
    db.close()

# Scenario 7: Follow-up after CREATE_TASK updates the created task in DB
def test_07_follow_up_after_create_task_updates_in_db():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # Step 1: Create task
    res1 = agent.execute_command("Create a task called 'Submit tax form' with high priority", db=db)
    assert res1.success is True
    created_id = res1.data["id"]
    assert TaskService.get_task_by_id(db, created_id).status == "Pending"

    # Step 2: Follow-up reference "that task"
    res2 = agent.execute_command("Mark that task as completed", db=db)
    assert res2.success is True
    assert res2.intent == "UPDATE_TASK"

    # Verify DB state
    updated_task = TaskService.get_task_by_id(db, created_id)
    assert updated_task.status == "Completed"
    assert updated_task.title == "Submit tax form"
    db.close()

# Scenario 8: Follow-up after GET_TASK updates the viewed task in DB
def test_08_follow_up_after_get_task_updates_in_db():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="First Task", priority="Low"))
    t2 = TaskService.create_task(db, TaskCreate(title="Second Task", priority="Low"))

    # Step 1: Show task 2
    res_get = agent.execute_command(f"Show task {t2.id}", db=db)
    assert res_get.success is True
    assert res_get.data["id"] == t2.id

    # Step 2: Follow-up reference "its"
    res_up = agent.execute_command("Set its priority to high", db=db)
    assert res_up.success is True
    assert res_up.intent == "UPDATE_TASK"

    # Verify DB state: t2 updated, t1 untouched
    t1_db = TaskService.get_task_by_id(db, t1.id)
    t2_db = TaskService.get_task_by_id(db, t2.id)
    assert t2_db.priority == "High"
    assert t1_db.priority == "Low"
    db.close()

# Scenario 9: Context cleared after DELETE_TASK: subsequent follow-up fails without deleting other tasks
def test_09_context_cleared_after_delete_task_prevents_wrong_task_deletion():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Task One"))
    t2 = TaskService.create_task(db, TaskCreate(title="Task Two"))
    t3 = TaskService.create_task(db, TaskCreate(title="Task Three"))
    assert len(TaskService.get_tasks(db)) == 3

    # Step 1: Delete task 2
    res_del1 = agent.execute_command(f"Delete task {t2.id}", db=db)
    assert res_del1.success is True

    # Step 2: Attempt to delete "that task" immediately after deletion
    res_del2 = agent.execute_command("Delete that task", db=db)
    assert res_del2.success is False

    # Verify DB state: Task 1 and Task 3 are STILL intact in DB!
    remaining_tasks = TaskService.get_tasks(db)
    assert len(remaining_tasks) == 2
    assert {t.id for t in remaining_tasks} == {t1.id, t3.id}
    db.close()

# Scenario 10: Follow-up with empty context memory on a fresh session fails cleanly with 0 DB changes
def test_10_follow_up_with_empty_context_memory_fails_cleanly():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    t1 = TaskService.create_task(db, TaskCreate(title="Existing Task", status="Pending", priority="Medium"))
    assert len(TaskService.get_tasks(db)) == 1

    # Follow-up "Complete it" on fresh session with empty context
    res = agent.execute_command("Complete it", db=db)
    assert res.success is False

    # Verify DB record was NOT modified or deleted
    t1_db = TaskService.get_task_by_id(db, t1.id)
    assert t1_db.status == "Pending"
    assert t1_db.priority == "Medium"
    assert len(TaskService.get_tasks(db)) == 1
    db.close()
