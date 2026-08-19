# TaskForge — AI-Powered Natural-Language Task Automation System

TaskForge is an AI-powered task automation system featuring a layered architecture, a local classical machine learning pipeline for intent classification and named entity recognition (NER), a conversational context memory system, and an explicit Planner/Executor workflow that operates on an SQLite database via FastAPI.

---

## 1. System Architecture

```text
User Natural-Language Input
    ↓
Intent Classification (TF-IDF + Calibrated Linear Classifier)
    ↓
Named Entity Recognition (BIO Token Sequence Labeler with Window Features)
    ↓
Entity Normalization & Validation (Dates, Priority, Category, Status, Ordinals)
    ↓
Conversational Context Resolution (Resolves "it", "its", "that task", "the first task", "the last task")
    ↓
Goal Understanding & Planner (Generates structured execution plan with validation steps)
    ↓
Executor (Validates and executes tool calls)
    ↓
TaskTool & TaskService
    ↓
SQLite Database (Persistent storage)
    ↓
Structured Agent Response
    ↓
Interactive Modern UI (Live Execution Inspector + Task Management Board)
```

---

## 2. Directory Structure

```text
taskforge/
├── ai/
│   ├── configs/
│   │   └── model_config.yaml          # Hyperparameters and model specifications
│   ├── data/
│   │   ├── intent_dataset.json        # Curated dataset for 6 intents
│   │   └── ner_dataset.json           # BIO-annotated token sequences
│   ├── preprocessing/
│   │   ├── text_preprocessor.py       # Regex tokenizer & whitespace normalization
│   │   └── feature_extractor.py       # Window-based token feature extraction
│   ├── training/
│   │   ├── train_intent.py            # Calibrated Linear Classifier trainer
│   │   ├── train_ner.py               # Token-level sequence classifier trainer
│   │   └── train_all.py               # Master training script
│   ├── evaluation/
│   │   └── evaluate.py                # Model evaluation and metrics reporter
│   ├── saved_models/
│   │   ├── intent_model.joblib        # Serialized intent model bundle
│   │   └── ner_model.joblib           # Serialized NER model bundle
│   └── inference/
│       ├── intent_classifier.py       # Runtime intent predictor with thresholding
│       ├── ner_extractor.py           # Runtime NER entity extractor
│       └── pipeline.py                # Unified AI inference interface
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── agent.py               # Master automation agent orchestrator
│   │   ├── api/
│   │   │   └── endpoints.py           # REST endpoints (/tasks, /agent/execute, /stats)
│   │   ├── core/
│   │   │   ├── config.py              # Application settings
│   │   │   └── errors.py              # Typed domain exceptions
│   │   ├── database/
│   │   │   └── session.py             # SQLAlchemy session and engine
│   │   ├── memory/
│   │   │   └── context_memory.py      # Conversational context memory
│   │   ├── models/
│   │   │   └── task.py                # Task database model
│   │   ├── schemas/
│   │   │   ├── task.py                # Task Pydantic schemas
│   │   │   └── agent.py               # Agent request, plan, response schemas
│   │   ├── services/
│   │   │   └── task_service.py        # Task management business logic
│   │   ├── tools/
│   │   │   └── task_tool.py           # Tool interface for the executor
│   │   ├── utils/
│   │   │   ├── normalizer.py          # Entity normalization
│   │   │   └── date_parser.py         # Natural date parsing (ISO format)
│   │   └── workflows/
│   │       ├── planner.py             # Execution plan generator
│   │       └── executor.py            # Plan executor and safety checks
│   └── main.py                        # FastAPI application entrypoint
├── frontend/
│   ├── index.html                     # Responsive UI layout
│   ├── style.css                      # Vanilla CSS design system
│   └── app.js                         # Dynamic UI and API controller
├── tests/
│   ├── test_backend.py                # REST CRUD and validation tests
│   ├── test_ai.py                     # Intent and NER inference tests
│   ├── test_agent.py                  # Planning, execution, context memory tests
│   └── test_e2e.py                    # Multi-turn conversational flow tests
├── requirements.txt
└── README.md
```

---

## 3. Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Train AI Models (Reproducible Offline Training)
```bash
python ai/training/train_all.py
```

### Step 3: Run the Automated Test Suite
```bash
python -m pytest tests/ -v
```

### Step 4: Launch TaskForge Server
```bash
python backend/main.py
```
Open your browser at **http://127.0.0.1:8000** to interact with TaskForge.

---

## 4. Key Capabilities & Conversational Examples

### Task Creation
- `"Create a task to learn FastAPI with medium priority in backend category tomorrow"`
- `"Add a high priority task to revise Python tomorrow"`
- `"Create a backend project called AI Task Manager"`

### Context-Aware Multi-Turn Sequences
```text
User: "Show task 1"
System: Displays Task 1 details

User: "Update its priority to low"
System: Resolves "its" -> Task 1, updates priority to Low

User: "Change its category to backend"
System: Resolves "its" -> Task 1, updates category to Backend

User: "Delete it"
System: Resolves "it" -> Task 1, safely deletes Task 1
```

### Ordinal References
- `"Show the first task"`
- `"Update its priority to high"`
- `"Show the previous task"`

### Safe Error Handling
- `"Delete task 9999"` -> Fails safely with `TASK_NOT_FOUND` (no silent deletions or hallucinations)
- `"What is quantum computing?"` -> Fails safely with `UNKNOWN_INTENT`
