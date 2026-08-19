from typing import Dict, Any
from .intent_classifier import IntentClassifier
from .ner_extractor import NERExtractor

class AIPipeline:
    """
    Unified local AI inference pipeline executing Intent Classification
    and Named Entity Recognition without any external LLM dependencies.
    """
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.ner_extractor = NERExtractor()

    def process(self, text: str) -> Dict[str, Any]:
        """
        Run the raw natural language through the AI pipeline.
        Returns:
            intent: Detected intent string
            confidence: Intent prediction confidence
            entities: Extracted entity dictionary
            raw_tokens: Token sequence
            raw_tags: BIO sequence tags
        """
        intent_res = self.intent_classifier.predict(text)
        ner_res = self.ner_extractor.extract_entities(text)

        return {
            "intent": intent_res["intent"],
            "confidence": intent_res["confidence"],
            "probabilities": intent_res["probabilities"],
            "entities": ner_res["entities"],
            "raw_tokens": ner_res["tokens"],
            "raw_tags": ner_res["tags"]
        }
