import os
import joblib
from pathlib import Path
from typing import Dict, Any

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "saved_models" / "intent_model.joblib"

class IntentClassifier:
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Intent model file not found at {model_path}. "
                "Run `python ai/training/train_all.py` first."
            )
        self.bundle = joblib.load(model_path)
        self.vectorizer = self.bundle["vectorizer"]
        self.classifier = self.bundle["classifier"]
        self.classes = self.bundle["classes"]
        self.confidence_threshold = self.bundle.get("confidence_threshold", 0.50)

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict intent with calibrated probability confidence score.
        If confidence is below threshold or ambiguous, returns UNKNOWN.
        """
        if not text or not text.strip():
            return {
                "intent": "UNKNOWN",
                "confidence": 0.0,
                "probabilities": {}
            }

        X = self.vectorizer.transform([text])
        probas = self.classifier.predict_proba(X)[0]
        
        prob_dict = {cls_name: float(p) for cls_name, p in zip(self.classes, probas)}
        sorted_probas = sorted(zip(self.classes, probas), key=lambda x: x[1], reverse=True)
        
        best_intent, best_confidence = sorted_probas[0]
        second_intent, second_confidence = sorted_probas[1] if len(sorted_probas) > 1 else ("", 0.0)

        # Ambiguity / OOD Check
        if best_confidence < self.confidence_threshold:
            final_intent = "UNKNOWN"
        elif (best_confidence - second_confidence) < 0.05 and best_confidence < 0.60:
            final_intent = "UNKNOWN"
        else:
            final_intent = best_intent

        return {
            "intent": final_intent,
            "confidence": round(float(best_confidence), 4),
            "probabilities": {k: round(v, 4) for k, v in prob_dict.items()}
        }
