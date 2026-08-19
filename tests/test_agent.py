import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.database.session import Base
from backend.app.services.task_service import TaskService
from backend.app.schemas.task import TaskCreate
from backend.app.tools.task_tool import TaskTool
from backend.app.memory.context_memory import ContextMemory
from backend.app.workflows.planner import Planner
from backend.app.workflows.executor import Executor
from backend.app.agents.agent import TaskForgeAgent
from backend.app.core.errors import MissingEntityError, TaskNotFoundError

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_planner_create_plan():
    plan = Planner.create_plan(
        intent="CREATE_TASK",
        confidence=0.95,
        entities={"title": "Master Algorithms", "priority": "High"},
        resolved_task_id=None,
        raw_query="Create task Master Algorithms with high priority"
    )
    assert plan.intent == "CREATE_TASK"
    assert len(plan.steps) == 3
    assert plan.steps[1].parameters["title"] == "Master Algorithms"
    assert plan.steps[1].parameters["priority"] == "High"

def test_planner_missing_title_raises():
    with pytest.raises(MissingEntityError):
        Planner.create_plan(
            intent="CREATE_TASK",
            confidence=0.9,
            entities={},
            resolved_task_id=None,
            raw_query="Create a task"
        )

def test_context_memory_pronoun_resolution():
    db = TestingSessionLocal()
    try:
        t1 = TaskService.create_task(db, TaskCreate(title="Initial Task", priority="Medium"))
        memory = ContextMemory()
        memory.record_turn("show task 1", "GET_TASK", task_id=t1.id)

        # "it" should resolve to t1.id
        resolved_id = memory.resolve_task_reference("update its priority to low", raw_task_id=None, db=db)
        assert resolved_id == t1.id

        resolved_id_delete = memory.resolve_task_reference("delete it", raw_task_id=None, db=db)
        assert resolved_id_delete == t1.id
    finally:
        db.close()

def test_context_memory_ordinal_resolution():
    db = TestingSessionLocal()
    try:
        t1 = TaskService.create_task(db, TaskCreate(title="First One", priority="Low"))
        t2 = TaskService.create_task(db, TaskCreate(title="Second One", priority="High"))
        memory = ContextMemory()

        first_id = memory.resolve_task_reference("show the first task", raw_task_id=None, db=db)
        assert first_id == t1.id

        last_id = memory.resolve_task_reference("show the last task", raw_task_id=None, db=db)
        assert last_id == t2.id
    finally:
        db.close()

def test_agent_safe_not_found():
    db = TestingSessionLocal()
    try:
        agent = TaskForgeAgent()
        res = agent.execute_command("delete task 9999", db=db)
        assert res.success is False
        assert res.error_type == "TASK_NOT_FOUND"
        assert "9999" in res.message
    finally:
        db.close()
