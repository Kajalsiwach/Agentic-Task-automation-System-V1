import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.train_intent import train_intent_model
from training.train_ner import train_ner_model

def train_all():
    print("=" * 60)
    print(" TASKFORGE AI PIPELINE TRAINING (CLASSICAL ML)")
    print("=" * 60)
    print("\n--- 1. Training Intent Classifier ---")
    train_intent_model()
    print("\n--- 2. Training NER Sequence Labeler ---")
    train_ner_model()
    print("\n" + "=" * 60)
    print(" [OK] All models successfully trained and serialized to disk!")
    print("=" * 60)

if __name__ == "__main__":
    train_all()
