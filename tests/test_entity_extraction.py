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
from backend.app.services.entity_normalizer import EntityExtractorNormalizer
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

# Case 1: CREATE_TASK - "Create a task to buy groceries with high priority due tomorrow"
def test_01_create_task_fallback_extraction():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Create a task to buy groceries with high priority due tomorrow",
        intent="CREATE_TASK",
        ner_entities={}  # Simulated empty NER
    )
    assert entities.get("title").lower() == "buy groceries"
    assert entities.get("priority") == "High"
    assert entities.get("due_date") is not None
    assert entities.get("deadline") == entities.get("due_date")

# Case 2: CREATE_TASK quoted title - 'Add task "Make sure tests pass" with urgent priority'
def test_02_create_task_quoted_title():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text='Add task "Make sure tests pass" with urgent priority',
        intent="CREATE_TASK",
        ner_entities={}
    )
    assert entities.get("title") == "Make sure tests pass"
    assert entities.get("priority") == "High"

# Case 3: GET_TASK by ID - "Show task #7"
def test_03_get_task_by_id():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Show task #7",
        intent="GET_TASK",
        ner_entities={}
    )
    assert entities.get("task_id") == 7

# Case 4: GET_TASK by title - "Find task called Prepare Q4 slides"
def test_04_get_task_by_title():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Find task called Prepare Q4 slides",
        intent="GET_TASK",
        ner_entities={}
    )
    assert entities.get("title") == "Prepare Q4 slides"

# Case 5: UPDATE_TASK status by ID - "Mark task 4 as completed"
def test_05_update_task_status_by_id():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Mark task 4 as completed",
        intent="UPDATE_TASK",
        ner_entities={}
    )
    assert entities.get("task_id") == 4
    assert entities.get("status") == "Completed"

# Case 6: UPDATE_TASK priority by title - "Set priority of task Deploy backend to high"
def test_06_update_task_priority_by_title():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Set priority of task Deploy backend to high",
        intent="UPDATE_TASK",
        ner_entities={}
    )
    assert entities.get("title") == "Deploy backend"
    assert entities.get("priority") == "High"

# Case 7: UPDATE_TASK rename by ID - 'Rename task 2 to "Updated API spec"'
def test_07_update_task_rename_by_id():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text='Rename task 2 to "Updated API spec"',
        intent="UPDATE_TASK",
        ner_entities={}
    )
    assert entities.get("task_id") == 2
    assert entities.get("new_title") == "Updated API spec"

# Case 8: UPDATE_TASK rename by title - 'Rename task "Draft email" to "Send final email"'
def test_08_update_task_rename_by_title():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text='Rename task "Draft email" to "Send final email"',
        intent="UPDATE_TASK",
        ner_entities={}
    )
    assert entities.get("title") == "Draft email"
    assert entities.get("new_title") == "Send final email"

# Case 9: DELETE_TASK by ID - "Delete task id 9"
def test_09_delete_task_by_id():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Delete task id 9",
        intent="DELETE_TASK",
        ner_entities={}
    )
    assert entities.get("task_id") == 9

# Case 10: DELETE_TASK by title - "Remove task Clean up logs"
def test_10_delete_task_by_title():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Remove task Clean up logs",
        intent="DELETE_TASK",
        ner_entities={}
    )
    assert entities.get("title") == "Clean up logs"

# Case 11: Date false-positive protection - "Create task Review 2026 roadmap due 2026-12-01"
def test_11_date_false_positive_protection():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Create task Review 2026 roadmap due 2026-12-01",
        intent="CREATE_TASK",
        ner_entities={}
    )
    assert entities.get("task_id") is None
    assert entities.get("due_date") == "2026-12-01"
    assert entities.get("deadline") == "2026-12-01"
    assert entities.get("title") == "Review 2026 roadmap"

# Case 12: NER precedence and normalization - when NER returns {"priority": "HIGH"} and misses title
def test_12_ner_precedence_and_normalization():
    entities = EntityExtractorNormalizer.extract_and_normalize(
        raw_text="Create a task to buy milk with high priority",
        intent="CREATE_TASK",
        ner_entities={"priority": "HIGH"}
    )
    assert entities.get("priority") == "High"
    assert entities.get("title").lower() == "buy milk"

# End-to-end agent execution with deterministic fallback
def test_end_to_end_agent_fallback_rename_and_lifecycle():
    db = TestingSessionLocal()
    agent = TaskForgeAgent()

    # 1. Create a task using natural language
    r_create = agent.execute_command(
        'Add task "Draft email" with urgent priority',
        db=db
    )
    assert r_create.success is True
    t_id = r_create.data["id"]
    assert r_create.data["title"] == "Draft email"
    assert r_create.data["priority"] == "High"

    # 2. Rename task by title using fallback extractor
    r_rename = agent.execute_command(
        'Rename task "Draft email" to "Send final email"',
        db=db
    )
    assert r_rename.success is True
    updated = TaskService.get_task_by_id(db, t_id)
    assert updated.title == "Send final email"

    # 3. Mark task as completed by ID
    r_mark = agent.execute_command(
        f"Mark task {t_id} as completed",
        db=db
    )
    assert r_mark.success is True
    updated_again = TaskService.get_task_by_id(db, t_id)
    assert updated_again.status == "Completed"

    # 4. Remove task by title
    r_del = agent.execute_command(
        'Remove task "Send final email"',
        db=db
    )
    assert r_del.success is True
    assert len(TaskService.get_tasks(db)) == 0

    db.close()
