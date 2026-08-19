import json
import os
import joblib
from pathlib import Path
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from preprocessing.feature_extractor import sentence_to_features

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "ner_dataset.json"
MODEL_DIR = BASE_DIR / "saved_models"
MODEL_PATH = MODEL_DIR / "ner_model.joblib"

def train_ner_model():
    print(f"[*] Loading NER data from {DATA_PATH}...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    X_features = []
    y_labels = []

    for sentence in data:
        tokens = sentence["tokens"]
        tags = sentence["tags"]
        feat_list = sentence_to_features(tokens)
        X_features.extend(feat_list)
        y_labels.extend(tags)

    print(f"[*] Total sentences: {len(data)}, Total tokens: {len(y_labels)}")
    print(f"[*] Unique entity tags: {sorted(list(set(y_labels)))}")

    vectorizer = DictVectorizer(sparse=True)
    X = vectorizer.fit_transform(X_features)

    classifier = LogisticRegression(
        C=4.0,
        max_iter=1000,
        random_state=42,
        solver="lbfgs"
    )
    classifier.fit(X, y_labels)

    # Evaluate
    preds = classifier.predict(X)
    acc = accuracy_score(y_labels, preds)
    print(f"[+] NER Token-level Training Accuracy: {acc * 100:.2f}%")
    print(classification_report(y_labels, preds))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "vectorizer": vectorizer,
        "classifier": classifier,
        "classes": list(classifier.classes_)
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"[+] NER model saved successfully to {MODEL_PATH}")
    return bundle

if __name__ == "__main__":
    train_ner_model()
