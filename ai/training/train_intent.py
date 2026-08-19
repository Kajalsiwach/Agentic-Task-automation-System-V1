import json
import os
import joblib
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, accuracy_score

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "intent_dataset.json"
MODEL_DIR = BASE_DIR / "saved_models"
MODEL_PATH = MODEL_DIR / "intent_model.joblib"

def train_intent_model():
    print(f"[*] Loading intent data from {DATA_PATH}...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = [item["text"] for item in data]
    labels = [item["intent"] for item in data]

    print(f"[*] Total training examples: {len(texts)}")
    print(f"[*] Unique intents: {sorted(list(set(labels)))}")

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        sublinear_tf=True,
        lowercase=True,
        strip_accents="unicode"
    )

    X = vectorizer.fit_transform(texts)
    
    # Classical Linear Classifier with Probability Calibration
    base_svc = LinearSVC(C=1.0, random_state=42, dual=False)
    # In sklearn 1.8+, estimator is the parameter name
    calibrated_clf = CalibratedClassifierCV(estimator=base_svc, cv=3)
    calibrated_clf.fit(X, labels)

    # Evaluate
    preds = calibrated_clf.predict(X)
    acc = accuracy_score(labels, preds)
    print(f"[+] Intent Model Training Accuracy: {acc * 100:.2f}%")
    print(classification_report(labels, preds))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "vectorizer": vectorizer,
        "classifier": calibrated_clf,
        "classes": list(calibrated_clf.classes_),
        "confidence_threshold": 0.50
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"[+] Intent model saved successfully to {MODEL_PATH}")
    return bundle

if __name__ == "__main__":
    train_intent_model()
