import os
import joblib
from pathlib import Path
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from preprocessing.text_preprocessor import tokenize, find_quoted_spans
from preprocessing.feature_extractor import sentence_to_features

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "saved_models" / "ner_model.joblib"

class NERExtractor:
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"NER model file not found at {model_path}. "
                "Run `python ai/training/train_all.py` first."
            )
        self.bundle = joblib.load(model_path)
        self.vectorizer = self.bundle["vectorizer"]
        self.classifier = self.bundle["classifier"]
        self.classes = self.bundle["classes"]

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract named entities from raw text.
        Returns both raw spans and assembled entity fields.
        """
        tokens = tokenize(text)
        if not tokens:
            return {
                "tokens": [],
                "tags": [],
                "entities": {}
            }

        features = sentence_to_features(tokens)
        X = self.vectorizer.transform(features)
        predicted_tags = self.classifier.predict(X)

        entities: Dict[str, str] = {}
        current_entity_type: Optional[str] = None
        current_tokens: List[str] = []

        for token, tag in zip(tokens, predicted_tags):
            if tag.startswith("B-"):
                if current_entity_type and current_tokens:
                    key = current_entity_type.lower()
                    val = " ".join([t for t in current_tokens if t not in ("'", '"', "`")])
                    if key not in entities or len(val) > len(entities[key]):
                        entities[key] = val
                current_entity_type = tag[2:]
                current_tokens = [token]
            elif tag.startswith("I-") and current_entity_type == tag[2:]:
                current_tokens.append(token)
            else:
                if current_entity_type and current_tokens:
                    key = current_entity_type.lower()
                    val = " ".join([t for t in current_tokens if t not in ("'", '"', "`")])
                    if key not in entities or len(val) > len(entities[key]):
                        entities[key] = val
                    current_entity_type = None
                    current_tokens = []

        if current_entity_type and current_tokens:
            key = current_entity_type.lower()
            val = " ".join([t for t in current_tokens if t not in ("'", '"', "`")])
            if key not in entities or len(val) > len(entities[key]):
                entities[key] = val

        # Post-processing for quoted titles:
        # If the user put explicit quotes around the title (e.g. called 'Study Computer Vision'),
        # ensure the entire quoted span is cleanly captured if title is missing or truncated.
        quoted = find_quoted_spans(text)
        if quoted:
            first_quoted = quoted[0][2]
            if "title" not in entities or len(first_quoted) > len(entities["title"]):
                # Only if text mentions task/called/named or CREATE/UPDATE
                entities["title"] = first_quoted

        return {
            "tokens": tokens,
            "tags": list(predicted_tags),
            "entities": entities
        }
