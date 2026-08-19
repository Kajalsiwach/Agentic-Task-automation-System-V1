import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.inference.pipeline import AIPipeline
from backend.app.utils.normalizer import normalize_entities

p = AIPipeline()

queries = [
    "Create a medium priority task called 'Study Computer Vision' in the AI category.",
    "Create a task to study Deep Learning with medium priority.",
    "Create a task to learn Machine Learning with high priority in the AI category.",
    "Create a task to study Deep Learning in Computer Vision with high priority.",
    "Create a task called 'Prepare ML presentation'.",
    "Update its category to AI.",
    "Update the last task's category to Project.",
    "Update task 14 category to Project.",
    "Update task 22 category to College.",
    "Update task 14 priority to High and category to Project.",
    "Delete all tasks."
]

for q in queries:
    res = p.process(q)
    norm = normalize_entities(res["entities"])
    print(f"Q: {q}")
    print(f"  Intent: {res['intent']} ({res['confidence']})")
    print(f"  Raw Entities: {res['entities']}")
    print(f"  Normalized: {norm}")
    print("-" * 50)
