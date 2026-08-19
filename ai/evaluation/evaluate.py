import json
import joblib
from pathlib import Path
from sklearn.metrics import classification_report, accuracy_score

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from preprocessing.feature_extractor import sentence_to_features

BASE_DIR = Path(__file__).resolve().parent.parent
INTENT_DATA = BASE_DIR / "data" / "intent_dataset.json"
NER_DATA = BASE_DIR / "data" / "ner_dataset.json"
INTENT_MODEL_PATH = BASE_DIR / "saved_models" / "intent_model.joblib"
NER_MODEL_PATH = BASE_DIR / "saved_models" / "ner_model.joblib"

def evaluate_models():
    print("[*] Evaluating Intent Classifier...")
    intent_bundle = joblib.load(INTENT_MODEL_PATH)
    vec = intent_bundle["vectorizer"]
    clf = intent_bundle["classifier"]

    with open(INTENT_DATA, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = [x["text"] for x in data]
    labels = [x["intent"] for x in data]

    X = vec.transform(texts)
    preds = clf.predict(X)
    print(f"Intent Model Accuracy: {accuracy_score(labels, preds) * 100:.2f}%")

    print("\n[*] Evaluating NER Sequence Model...")
    ner_bundle = joblib.load(NER_MODEL_PATH)
    ner_vec = ner_bundle["vectorizer"]
    ner_clf = ner_bundle["classifier"]

    with open(NER_DATA, "r", encoding="utf-8") as f:
        ner_data = json.load(f)

    X_feats, y_tags = [], []
    for sent in ner_data:
        feats = sentence_to_features(sent["tokens"])
        X_feats.extend(feats)
        y_tags.extend(sent["tags"])

    X_ner = ner_vec.transform(X_feats)
    ner_preds = ner_clf.predict(X_ner)
    print(f"NER Model Accuracy: {accuracy_score(y_tags, ner_preds) * 100:.2f}%")

if __name__ == "__main__":
    evaluate_models()
