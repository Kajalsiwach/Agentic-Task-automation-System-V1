import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai.inference.intent_classifier import IntentClassifier
from ai.inference.ner_extractor import NERExtractor
from backend.app.utils.normalizer import normalize_entities, normalize_priority, normalize_status
from backend.app.utils.date_parser import parse_natural_date

@pytest.fixture(scope="module")
def intent_clf():
    return IntentClassifier()

@pytest.fixture(scope="module")
def ner_ext():
    return NERExtractor()

def test_intent_classification(intent_clf):
    res_create = intent_clf.predict("Create a task to learn FastAPI with medium priority")
    assert res_create["intent"] == "CREATE_TASK"
    assert res_create["confidence"] > 0.5

    res_get_all = intent_clf.predict("Show all my tasks")
    assert res_get_all["intent"] == "GET_TASKS"

    res_get_one = intent_clf.predict("Show task 9")
    assert res_get_one["intent"] == "GET_TASK"

    res_update = intent_clf.predict("Update task 9 priority to low")
    assert res_update["intent"] == "UPDATE_TASK"

    res_delete = intent_clf.predict("Delete task 1")
    assert res_delete["intent"] == "DELETE_TASK"

    res_unknown = intent_clf.predict("What is the recipe for chocolate cake?")
    assert res_unknown["intent"] == "UNKNOWN"

def test_ner_extraction(ner_ext):
    res = ner_ext.extract_entities("Create a task to learn FastAPI with medium priority in backend category tomorrow")
    entities = res["entities"]
    assert "title" in entities
    assert "fastapi" in entities["title"].lower()
    assert "priority" in entities
    assert entities["priority"].lower() == "medium"
    assert "category" in entities
    assert "backend" in entities["category"].lower()
    assert "deadline" in entities
    assert "tomorrow" in entities["deadline"].lower()

def test_normalization():
    assert normalize_priority("urgent") == "High"
    assert normalize_priority("med") == "Medium"
    assert normalize_priority("minor") == "Low"
    assert normalize_status("done") == "Completed"
    assert normalize_status("open") == "Pending"

    parsed_date = parse_natural_date("tomorrow")
    assert parsed_date is not None
    assert len(parsed_date) == 10  # YYYY-MM-DD format

    norm_dict = normalize_entities({
        "title": "to learn FastAPI",
        "priority": "urgent",
        "category": "backend project",
        "deadline": "tomorrow"
    })
    assert norm_dict["title"] == "learn FastAPI"
    assert norm_dict["priority"] == "High"
    assert norm_dict["category"] == "Backend"
    assert norm_dict["deadline"] == parsed_date
