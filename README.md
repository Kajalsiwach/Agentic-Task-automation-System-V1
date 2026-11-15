# TaskForge — AI Task Automation & Analytics System

TaskForge is an AI-powered task management system that lets you manage your daily tasks using natural English commands or an interactive web dashboard. It combines lightweight machine learning with deterministic safety rules to understand requests, maintain conversational context, protect against accidental changes, and provide visual productivity analytics.

---

## Key Features

- **Natural Language Task Commands**  
  Add, update, view, or delete tasks naturally without filling out complex forms.
  - *Example:* `"Create a task to prepare sprint demo with high priority due tomorrow"`
  - *Example:* `"Find task called Review Q4 report"`

- **Context Memory & Follow-ups**  
  Follow up on previously mentioned tasks using pronouns or relative phrases like `"it"`, `"that task"`, or `"the first task"`.
  - *Example:* `"Show task 2"` → `"Mark it as completed"` → `"Update its priority to low"`

- **Safe Task Resolution & Disambiguation**  
  If multiple tasks share a similar title, TaskForge stops and asks for clarification instead of guessing or modifying the wrong task.

- **Safe Deletion Protection**  
  Bulk deletion (`Delete all tasks`) requires an explicit standalone confirmation (`"yes"`). Unrelated commands automatically cancel the pending deletion, preventing accidental data loss.

- **Interactive Analytics & Productivity Dashboard**  
  A visual dashboard with real-time charts to track workload and progress:
  - **Completion Trend:** Daily chart of tasks completed over time.
  - **Status Breakdown:** Visual split between Pending, Completed, and Overdue tasks.
  - **Priority Distribution:** Task counts across High, Medium, and Low tiers.
  - **Category Distribution:** Dynamic distribution across custom tags/projects.
  - **Date Range Selector:** View data for the Last 7 Days, Last 30 Days, or All Time.

- **Guaranteed Database Verification**  
  Every change is verified directly against the SQLite database before confirming success to the user.

---

## How It Works

```
User Input (Natural Language or UI)
   │
   ▼
1. Intent & Entity Extraction (Identifies what you want to do and extracts title, priority, date, category)
   │
   ▼
2. Normalization & Safety Guardrails (Cleans input, resolves dates, checks pronouns and context memory)
   │
   ▼
3. Request Validation (Validates all required fields and checks for confirmation if deleting)
   │
   ▼
4. Database Execution & Verification (Applies change to SQLite and verifies the stored record)
   │
   ▼
5. Response & Live Dashboard (Updates the UI, task list, and interactive charts)
```

---

## Project Structure

```text
task_automation/
├── ai/
│   ├── configs/                  # Model configurations
│   ├── data/                     # Training datasets for intents and entities
│   ├── inference/                # Real-time intent classifier and entity extractor
│   ├── saved_models/             # Pre-trained ML model files
│   └── training/                 # Offline model training scripts
├── backend/
│   ├── app/
│   │   ├── agents/               # Main agent orchestrator
│   │   ├── api/                  # REST API endpoints (/tasks, /agent, /analytics, /health)
│   │   ├── core/                 # Settings and typed error definitions
│   │   ├── database/             # SQLite connection and session management
│   │   ├── memory/               # Conversational context memory
│   │   ├── models/               # SQLAlchemy database models
│   │   ├── schemas/              # Pydantic data schemas & request contracts
│   │   ├── services/             # Business logic (tasks, analytics, validation, resolver)
│   │   ├── tools/                # Database execution tools
│   │   ├── utils/                # Date parsing and entity normalization helpers
│   │   └── workflows/            # Plan formulation and verified execution
│   └── main.py                   # FastAPI application entrypoint
├── frontend/
│   ├── index.html                # Responsive web dashboard layout
│   ├── style.css                 # Clean blue-and-white stylesheet
│   ├── app.js                    # UI interaction, chat console, and Chart.js controller
│   └── chart.umd.js              # Standalone Chart.js library (bundled for reliability)
├── tests/                        # 12 test suites (91 automated tests)
├── requirements.txt              # Project Python dependencies
└── README.md                     # Project documentation
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+**
- Git

### 2. Installation
Clone the repository and install the required dependencies:

```bash
git clone https://github.com/Kajalsiwach/Agentic-Task-automation-System-V1.git
cd Agentic-Task-automation-System-V1
pip install -r requirements.txt
```

### 3. Start the Application
Run the FastAPI development server:

```bash
uvicorn backend.main:app --reload
```

The application will be live at:
- **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Example Natural Language Commands

You can type these directly into the chat bar on the dashboard or send them via the `/api/agent/execute` API endpoint:

| Command | Action |
|---|---|
| `"Create a task to prepare sprint demo with high priority due tomorrow"` | Creates task with title, High priority, and tomorrow's date |
| `"Add task Review Q4 report in category Finance"` | Creates task with category `"Finance"` |
| `"List all tasks"` | Displays all stored tasks |
| `"Show task 1"` | Displays details for Task #1 and sets it in context |
| `"Mark it as completed"` | Updates the task currently in context to `Completed` |
| `"Update its priority to low"` | Changes the priority of the context task to `Low` |
| `"Rename task 2 to Review Final Q4 Report"` | Updates the title of Task #2 |
| `"Delete task Review Final Q4 Report"` | Deletes the specific task safely |
| `"Delete all tasks"` | Triggers safety prompt: requires `"yes"` to proceed |

---

## REST API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` or `/api/health` | Service health status |
| `GET` | `/tasks` | List all tasks (supports filtering by `status`, `priority`, `category`) |
| `POST` | `/tasks` | Create a task directly via structured JSON |
| `GET` | `/tasks/{id}` | Retrieve a task by ID |
| `PUT` | `/tasks/{id}` | Update task fields (status, priority, deadline, category) |
| `DELETE` | `/tasks/{id}` | Delete a task by ID |
| `DELETE` | `/tasks` | Delete all tasks |
| `POST` | `/api/agent/execute` | Execute a natural language task command |
| `GET` | `/api/agent/context` | View active conversational memory state |
| `POST` | `/api/agent/context/reset` | Clear context memory |
| `GET` | `/stats` | High-level task summary metrics |
| `GET` | `/analytics/overview` | Full analytics payload for all 4 charts (`?range=7d\|30d\|all`) |

---

## Testing & Quality Assurance

TaskForge includes an automated test suite covering unit tests, API tests, entity extraction, context memory, and end-to-end user workflows:

```bash
python -m pytest tests/ -v
```

**Test Suite Coverage:**
- `test_agent.py`: Agent planning and context resolution.
- `test_ai.py`: ML model inference and token extraction.
- `test_analytics.py`: Real-time chart metric calculations and date filtering.
- `test_backend.py`: Core REST API operations.
- `test_e2e.py`: Multi-turn conversational flows.
- `test_e2e_http_commands.py`: Live HTTP boundary testing across user scenarios.
- `test_entity_extraction.py`: Deterministic fallback rules for dates, titles, and priorities.
- `test_intent_and_verification.py`: Intent guardrails and post-execution DB state verification.
- `test_regression.py`: Edge cases, bad inputs, and safety handling.
- `test_safe_confirmation.py`: Two-step bulk delete confirmation rules.
- `test_task_resolution.py`: Ambiguous title matching and safe error reporting.
- `test_validation_contract.py`: Centralized request contract validation.

**Result: 91 passed out of 91 tests (100% pass rate).**

---

## License

This project is open-source and available under the standard MIT License.
