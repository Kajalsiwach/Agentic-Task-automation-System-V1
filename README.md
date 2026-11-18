# TaskForge — AI-Powered Task Automation & Analytics Platform

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-FastAPI%20%7C%20Uvicorn-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/database-SQLite%20%7C%20SQLAlchemy-003B57.svg)](https://www.sqlalchemy.org/)
[![Machine Learning](https://img.shields.io/badge/ML%20Library-Scikit--learn-F7931E.svg)](https://scikit-learn.org/)
[![Automated Tests](https://img.shields.io/badge/tests-91%20passed%20(100%25)-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TaskForge is an enterprise-grade task automation and productivity platform that translates conversational natural language commands into validated database operations. Built with a **hybrid neuro-symbolic architecture**, TaskForge pairs local classical machine learning (TF-IDF + Calibrated LinearSVC for intent classification, and token-level Logistic Regression for BIO entity extraction) with deterministic request contracts, multi-turn conversational context memory, safety confirmation gates, and post-execution database verification.

---

## Key Features

- **Natural Language Task Management**  
  Execute CRUD operations via plain English sentences without navigating rigid form fields or multi-step modals.
  - *Example:* `"Create a task to prepare sprint demo with high priority due tomorrow"`
  - *Example:* `"Find task called Review Q4 report"`

- **Conversational Context Memory**  
  Maintains active conversational state across turns, resolving referential pronouns (`"it"`, `"its"`, `"that task"`) and ordinal references (`"the first task"`, `"the last task"`).
  - *Example:* `"Show task 2"` $\rightarrow$ `"Mark it as completed"` $\rightarrow$ `"Update its priority to low"`

- **Deterministic Task Disambiguation**  
  Protects against modifying the wrong record using a 4-tier resolution hierarchy (ID match $\rightarrow$ exact title match $\rightarrow$ substring match $\rightarrow$ candidate error listing). If multiple tasks match, execution halts and returns candidate options.

- **Safe Confirmation Gate for Destructive Actions**  
  Bulk deletion (`DELETE_ALL_TASKS`) requires explicit standalone confirmation (`"yes"`). Unrelated commands automatically cancel pending deletions, preventing accidental data loss.

- **Post-Execution Database State Verification**  
  Every database write operation (`CREATE`, `UPDATE`, `DELETE`) is re-queried directly from SQLite on disk before returning a success response, ensuring zero phantom state changes.

- **Interactive Productivity Analytics Dashboard**  
  A visual dashboard powered by Chart.js featuring 4 interactive charts dynamically filtered by time range (`7d`, `30d`, `all`):
  - **Completion Trend:** Daily task completion velocity over time.
  - **Status Breakdown:** Distribution of Pending, Completed, and Overdue tasks.
  - **Priority Distribution:** Task allocation across High, Medium, and Low tiers.
  - **Category Distribution:** Dynamic distribution across custom tags and domains.

- **100% Local & Privacy-Preserving Execution**  
  Zero dependency on external cloud LLM APIs. Operates completely offline with sub-millisecond inference and zero cloud operational costs.

---

## System Architecture

```
User Input (Web Console or REST API)
   │
   ▼
[ FastAPI Routing Layer (/api/agent/execute) ]
   │
   ▼
[ Step 1: Safety Interceptor & Confirmation Gate ]
   ├─► Standalone Confirmation ("yes") ──► Execute Pending Bulk Action
   ├─► Unrelated Command ───────────────► Cancel Pending Action & Continue
   └─► Normal Input ────────────────────► Forward to Intent Guardrail
   │
   ▼
[ Step 2: Intent Classification & Named Entity Recognition ]
   ├─► Intent Model: TF-IDF (1-3 N-Grams) + LinearSVC + Sigmoid Probability Calibration
   └─► NER Model: Window Features + DictVectorizer + Logistic Regression (BIO Tagging)
   │
   ▼
[ Step 3: Deterministic Normalization & Context Resolution ]
   ├─► Normalizer: Maps dates to ISO YYYY-MM-DD, standardizes priorities & statuses
   ├─► ContextMemory: Resolves pronouns ("it", "its") to active task ID
   └─► TaskResolver: Applies 4-tier disambiguation (ID -> Exact -> Partial -> Candidates)
   │
   ▼
[ Step 4: Request Contract Validation & Planning ]
   ├─► RequestValidator: Enforces StructuredRequest contract; blocks missing entities
   └─► Planner: Builds atomic ExecutionPlan [Validate -> Execute Tool -> Format]
   │
   ▼
[ Step 5: Execution & Post-Execution Database Verification ]
   ├─► TaskTool & TaskService: Executes database operations via SQLAlchemy ORM
   ├─► SQLite Storage: Persists rows directly to backend/data/taskforge.db
   └─► State Verification: Re-queries SQLite on disk to prove persistence
   │
   ▼
[ Output: Structured AgentResponse & Real-Time Dashboard Update ]
```

---

## Machine Learning & NLP Subsystems

TaskForge uses classical, interpretable machine learning pipelines paired with deterministic guardrails:

### 1. Intent Classification Pipeline
- **Vectorization:** `TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True, max_features=3000, strip_accents='unicode')`. Captures unigram, bigram, and trigram phrases.
- **Classifier:** `LinearSVC(C=1.0, dual=False)`. Finds the maximum-margin hyperplane separating intents in sparse text space.
- **Calibration:** `CalibratedClassifierCV(method='sigmoid', cv=3)`. Applies Platt sigmoid scaling to convert SVM margins into calibrated probabilities ($[0, 1]$).
- **Decision & OOD Rejection:** Requires top confidence $\ge 0.50$ and margin gap $\ge 0.05$. Inputs below threshold default safely to `UNKNOWN`.
- **Supported Intents (7 Classes):** `CREATE_TASK`, `GET_TASK`, `GET_TASKS`, `UPDATE_TASK`, `DELETE_TASK`, `DELETE_ALL_TASKS`, `UNKNOWN`.

### 2. Named Entity Recognition (NER) Sequence Model
- **Token Feature Extractor:** Extracts word casing, length, word shape (`Xxxx`, `dd`), prefixes/suffixes, and neighboring contextual tokens ($i-1, i-2, i+1, i+2$).
- **Vectorization:** `DictVectorizer(sparse=True)`.
- **Sequence Classifier:** `LogisticRegression(C=4.0, max_iter=1000, solver='lbfgs')`.
- **Tagging Scheme:** BIO Standard (`B-TITLE`, `I-TITLE`, `B-PRIORITY`, `B-DEADLINE`, `I-DEADLINE`, `B-CATEGORY`, `B-STATUS`, `B-TASK_ID`, `I-TASK_ID`, `B-DESCRIPTION`, `I-DESCRIPTION`, `O`).
- **Deterministic Fallback Layer:** `EntityExtractorNormalizer` provides regex-based fallback extraction if statistical sequence labeling under-segments.

---

## Technology Stack

| Layer | Component | Version | Purpose |
|---|---|---|---|
| **Backend & API** | FastAPI | `>=0.110.0` | Asynchronous REST API routing, request validation, and OpenAPI documentation |
| **ASGI Server** | Uvicorn | `>=0.28.0` | Production ASGI web server running with auto-reloading |
| **Data Contracts** | Pydantic | `>=2.0.0` | Strict data schemas (`StructuredRequest`, `AgentResponse`, `TaskCreate`) |
| **Database & ORM** | SQLAlchemy | `>=2.0.0` | Object-Relational Mapping (ORM) and transaction management |
| **Database Engine** | SQLite | `3.x` | Embedded relational database (`backend/data/taskforge.db`) |
| **Machine Learning** | Scikit-learn | `>=1.4.0` | TF-IDF vectorization, LinearSVC with calibration, Logistic Regression BIO NER |
| **Model Storage** | Joblib | `>=1.3.0` | Serialization/deserialization of pre-trained model bundles |
| **Date Parsing** | Python-Dateutil | `2.9.x` | Natural language temporal normalization to ISO format (`YYYY-MM-DD`) |
| **Frontend UI** | HTML5 / CSS3 / ES6+ | Native | Clean blue-and-white dashboard, chat console, and execution inspector |
| **Data Visualization** | Chart.js | `v4.4.1` | Bundled JavaScript visualization engine rendering 4 interactive canvas charts |
| **Testing** | Pytest | `>=8.0.0` | Automated test suite covering unit, integration, and HTTP smoke tests |

---

## Project Structure

```text
task_automation/
├── ai/
│   ├── configs/                  # Hyperparameter configuration (model_config.yaml)
│   ├── data/                     # Curated training data (intent_dataset.json, ner_dataset.json)
│   ├── evaluation/               # Model evaluation scripts (evaluate.py)
│   ├── inference/                # Runtime inference pipeline (intent_classifier.py, ner_extractor.py, pipeline.py)
│   ├── preprocessing/            # Text tokenization and window feature extraction (text_preprocessor.py, feature_extractor.py)
│   ├── saved_models/             # Serialized model bundles (intent_model.joblib, ner_model.joblib)
│   └── training/                 # Model training scripts (train_intent.py, train_ner.py, train_all.py)
├── backend/
│   ├── app/
│   │   ├── agents/               # Main agent orchestrator (agent.py)
│   │   ├── api/                  # REST endpoints for tasks, agent execution, stats, and analytics (endpoints.py)
│   │   ├── core/                 # Typed error hierarchy (errors.py) and app settings (config.py)
│   │   ├── database/             # SQLite connection and session management (session.py)
│   │   ├── memory/               # Conversational context memory (context_memory.py)
│   │   ├── models/               # SQLAlchemy ORM models (task.py)
│   │   ├── schemas/              # Pydantic schemas (task.py, agent.py, request_contract.py, analytics.py)
│   │   ├── services/             # Business logic (task_service.py, analytics_service.py, request_validator.py, task_resolver.py)
│   │   ├── tools/                # Database execution tools (task_tool.py)
│   │   ├── utils/                # Normalization and date parsing (normalizer.py, date_parser.py)
│   │   └── workflows/            # Execution planning (planner.py) and verified execution (executor.py)
│   └── main.py                   # FastAPI application entrypoint
├── frontend/
│   ├── index.html                # Responsive dashboard and analytics layout
│   ├── style.css                 # Clean CSS design system
│   ├── app.js                    # UI controller, API client, and Chart.js integration
│   └── chart.umd.js              # Standalone Chart.js library (bundled for offline reliability)
├── tests/                        # 12 test suites (91 automated tests)
├── requirements.txt              # Production Python dependencies
├── .gitignore                    # Version control exclusion rules
└── README.md                     # Project documentation
```

---

## REST API Reference

### Task Management Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|:---:|
| `GET` | `/health` | Service health check | `200 OK` |
| `GET` | `/api/health` | API router health check | `200 OK` |
| `GET` | `/tasks` | List tasks (supports `status`, `priority`, `category`, `search` filters) | `200 OK` |
| `POST` | `/tasks` | Create task via structured JSON payload | `201 Created` |
| `GET` | `/tasks/{id}` | Retrieve task by ID | `200 OK` / `404 Not Found` |
| `PUT` | `/tasks/{id}` | Update task fields (`title`, `priority`, `deadline`, `status`, `category`) | `200 OK` / `404 Not Found` |
| `DELETE` | `/tasks/{id}` | Delete task by ID | `200 OK` / `404 Not Found` |
| `DELETE` | `/tasks` | Bulk delete all tasks | `200 OK` |

### Natural Language & Agent Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|:---:|
| `POST` | `/api/agent/execute` | Process natural language task command | `200 OK` |
| `GET` | `/api/agent/context` | View active conversational memory state | `200 OK` |
| `POST` | `/api/agent/context/reset` | Clear conversational context memory | `200 OK` |

### Analytics & Reporting Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|:---:|
| `GET` | `/stats` | High-level task summary metrics | `200 OK` |
| `GET` | `/analytics/overview` | Complete 4-chart payload (`?range=7d\|30d\|all`) | `200 OK` |
| `GET` | `/analytics/completion-trend` | Daily task completion velocity data | `200 OK` |
| `GET` | `/analytics/status-distribution` | Task status counts with overdue breakdown | `200 OK` |
| `GET` | `/analytics/priority-distribution` | Task counts across High, Medium, and Low tiers | `200 OK` |
| `GET` | `/analytics/category-distribution` | Category-wise task breakdown | `200 OK` |

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+**
- Git

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/Kajalsiwach/Agentic-Task-automation-System-V1.git
cd Agentic-Task-automation-System-V1

# Install dependencies
pip install -r requirements.txt
```

### 3. Model Training (Optional - Pre-Trained Artifacts Included)
```bash
# Retrain intent classification and NER models
python ai/training/train_all.py
```

### 4. Run the Application
```bash
# Start the FastAPI server with auto-reload
uvicorn backend.main:app --reload
```

Access the application:
- **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger UI Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Testing & Quality Assurance

TaskForge includes an automated test suite verifying business logic, API endpoints, intent classification, context memory, and live HTTP boundaries:

```bash
# Run the complete test suite
python -m pytest tests/ -v
```

### Test Suite Breakdown

| Test Suite | Focus Area | Test Count | Status |
|---|---|:---:|:---:|
| `test_agent.py` | Agent planning, context memory resolution, safe errors | 5 | **PASSED** |
| `test_ai.py` | Intent classification, token sequence NER, normalization | 3 | **PASSED** |
| `test_analytics.py` | Analytics endpoints, status distribution, overdue logic, date filters | 5 | **PASSED** |
| `test_backend.py` | Core CRUD operations, filtering, and model validation | 6 | **PASSED** |
| `test_e2e.py` | Multi-turn conversational workflows through the agent | 3 | **PASSED** |
| `test_e2e_http_commands.py` | Live HTTP boundary tests via FastAPI TestClient (11 user scenarios) | 10 | **PASSED** |
| `test_entity_extraction.py` | Deterministic fallback rules for titles, dates, priorities, and IDs | 13 | **PASSED** |
| `test_intent_and_verification.py` | Intent classification guardrails and post-execution DB verification | 10 | **PASSED** |
| `test_regression.py` | Edge cases, malformed queries, and graceful error handling | 6 | **PASSED** |
| `test_safe_confirmation.py` | Two-step confirmation gates and non-inheritance protection | 10 | **PASSED** |
| `test_task_resolution.py` | 4-tier task resolution hierarchy and ambiguity handling | 10 | **PASSED** |
| `test_validation_contract.py` | StructuredRequest contracts and centralized RequestValidator | 10 | **PASSED** |

**Total: 91 / 91 tests passed (100% pass rate, 0 failures, 0 regressions).**

---

## Model Evaluation Metrics

Models were evaluated using **5-Fold Stratified Cross-Validation** to measure generalization across held-out validation folds:

| Subsystem | Metric | Cross-Validation Score | Notes |
|---|---|:---:|---|
| **Intent Classifier** | Accuracy | **80.57%** | Correctly predicts user action across unseen validation folds |
| **Intent Classifier** | Macro F1-Score | **0.7443** | Unweighted harmonic mean across all 7 intent classes |
| **NER Sequence Model** | Token Accuracy | **92.31%** | Token-level sequence classification accuracy |
| **NER Sequence Model** | Macro F1-Score | **0.6651** | Balanced metric across all 12 BIO entity tags |

---

## Security & Operational Safeguards

- **No Remote Code Execution (RCE):** The planner and executor only invoke pre-defined, typed methods in `TaskTool`.
- **Zero Cloud Exposure:** No user task data or queries are transmitted to third-party cloud services or APIs.
- **Transactional State Verification:** Prevents phantom execution by re-querying SQLite database rows directly on disk.
- **Destructive Operation Guards:** Bulk deletion cannot be executed without explicit, standalone user authorization.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
