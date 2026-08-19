/* ==========================================================================
   TaskForge — Interactive Frontend Controller
   ========================================================================== */

const API_BASE = "";

// State
let allTasks = [];
let activeStatusFilter = "";
let activePriorityFilter = "";
let activeSearchQuery = "";

// DOM Elements
const agentCommandInput = document.getElementById("agentCommandInput");
const agentExecuteBtn = document.getElementById("agentExecuteBtn");
const resetMemoryBtn = document.getElementById("resetMemoryBtn");
const aiInspector = document.getElementById("aiInspector");
const intentName = document.getElementById("intentName");
const intentConfidence = document.getElementById("intentConfidence");
const entityTagsContainer = document.getElementById("entityTagsContainer");
const planStepsList = document.getElementById("planStepsList");
const agentMessageBanner = document.getElementById("agentMessageBanner");
const inspectorStatusBadge = document.getElementById("inspectorStatusBadge");

const metricTotal = document.getElementById("metricTotal");
const metricPending = document.getElementById("metricPending");
const metricCompleted = document.getElementById("metricCompleted");
const metricHigh = document.getElementById("metricHigh");

const tasksGrid = document.getElementById("tasksGrid");
const emptyState = document.getElementById("emptyState");
const taskCountSubtitle = document.getElementById("taskCountSubtitle");
const taskSearchInput = document.getElementById("taskSearchInput");
const statusFilterButtons = document.querySelectorAll(".filter-btn");
const priorityFilterSelect = document.getElementById("priorityFilterSelect");

const taskModal = document.getElementById("taskModal");
const modalTitle = document.getElementById("modalTitle");
const taskForm = document.getElementById("taskForm");
const formTaskId = document.getElementById("formTaskId");
const formTitle = document.getElementById("formTitle");
const formDescription = document.getElementById("formDescription");
const formPriority = document.getElementById("formPriority");
const formCategory = document.getElementById("formCategory");
const formDeadline = document.getElementById("formDeadline");
const formStatus = document.getElementById("formStatus");
const openCreateModalBtn = document.getElementById("openCreateModalBtn");
const closeModalBtn = document.getElementById("closeModalBtn");
const cancelModalBtn = document.getElementById("cancelModalBtn");

// ---------------- Initialization ----------------

document.addEventListener("DOMContentLoaded", () => {
  fetchTasks();
  fetchStats();
  setupEventListeners();
});

function setupEventListeners() {
  // AI Command Execution
  agentExecuteBtn.addEventListener("click", handleAgentExecute);
  agentCommandInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      handleAgentExecute();
    }
  });

  // Suggestion Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const cmd = chip.getAttribute("data-cmd");
      agentCommandInput.value = cmd;
      handleAgentExecute();
    });
  });

  // Reset Memory
  resetMemoryBtn.addEventListener("click", async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/context/reset`, { method: "POST" });
      const data = await res.json();
      showInspectorFeedback("Context Memory Reset", "UNKNOWN", 1.0, {}, [], data.message, true);
    } catch (err) {
      console.error("Error resetting context:", err);
    }
  });

  // Search & Filters
  taskSearchInput.addEventListener("input", (e) => {
    activeSearchQuery = e.target.value.toLowerCase().trim();
    renderTasks();
  });

  statusFilterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      statusFilterButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeStatusFilter = btn.getAttribute("data-status");
      renderTasks();
    });
  });

  priorityFilterSelect.addEventListener("change", (e) => {
    activePriorityFilter = e.target.value;
    renderTasks();
  });

  // Modal handlers
  openCreateModalBtn.addEventListener("click", () => openModal());
  closeModalBtn.addEventListener("click", closeModal);
  cancelModalBtn.addEventListener("click", closeModal);
  taskModal.addEventListener("click", (e) => {
    if (e.target === taskModal) closeModal();
  });

  taskForm.addEventListener("submit", handleFormSubmit);
}

// ---------------- AI Agent Execution ----------------

async function handleAgentExecute() {
  const goal = agentCommandInput.value.trim();
  if (!goal) return;

  agentExecuteBtn.disabled = true;
  agentExecuteBtn.innerHTML = "Thinking...";

  try {
    const response = await fetch(`${API_BASE}/agent/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    });

    const result = await response.json();
    renderInspector(result);

    // Refresh task state and metrics
    await fetchTasks();
    await fetchStats();

  } catch (error) {
    console.error("Agent execution failed:", error);
    showInspectorFeedback("Error", "UNKNOWN", 0.0, {}, [], "Network error contacting TaskForge backend.", false);
  } finally {
    agentExecuteBtn.disabled = false;
    agentExecuteBtn.innerHTML = `
      <span>Execute</span>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
      </svg>
    `;
  }
}

function renderInspector(result) {
  aiInspector.classList.remove("hidden");

  const success = result.success;
  inspectorStatusBadge.textContent = success ? "Plan Executed" : (result.error_type || "Clarification Needed");
  inspectorStatusBadge.className = success ? "badge-success" : "badge-error";

  intentName.textContent = result.intent || "UNKNOWN";
  const confPct = result.confidence ? `${(result.confidence * 100).toFixed(1)}%` : "N/A";
  intentConfidence.textContent = confPct;

  // Extracted Entities
  entityTagsContainer.innerHTML = "";
  const entities = result.plan ? result.plan.resolved_entities : {};
  const entityKeys = Object.keys(entities);

  if (entityKeys.length === 0) {
    entityTagsContainer.innerHTML = `<span style="font-size:0.75rem; color:#94a3b8;">None extracted</span>`;
  } else {
    entityKeys.forEach((key) => {
      const tag = document.createElement("div");
      tag.className = "entity-tag";
      tag.innerHTML = `
        <span class="entity-tag-key">${key.toUpperCase()}:</span>
        <span class="entity-tag-val">${entities[key]}</span>
      `;
      entityTagsContainer.appendChild(tag);
    });
  }

  // Plan Steps
  planStepsList.innerHTML = "";
  if (result.plan && result.plan.steps && result.plan.steps.length > 0) {
    result.plan.steps.forEach((step) => {
      const li = document.createElement("li");
      li.className = "plan-step-item";
      li.innerHTML = `
        <span class="step-num">${step.step_number}</span>
        <span>${step.description}</span>
      `;
      planStepsList.appendChild(li);
    });
  } else {
    planStepsList.innerHTML = `<li class="plan-step-item" style="color:#94a3b8;">No execution steps generated.</li>`;
  }

  // Result Banner
  agentMessageBanner.textContent = result.message;
  agentMessageBanner.style.background = success ? "rgba(37, 99, 235, 0.15)" : "rgba(220, 38, 38, 0.15)";
  agentMessageBanner.style.borderColor = success ? "rgba(37, 99, 235, 0.3)" : "rgba(220, 38, 38, 0.3)";
  agentMessageBanner.style.color = success ? "#93c5fd" : "#fca5a5";
}

function showInspectorFeedback(title, intent, confidence, entities, steps, message, success) {
  aiInspector.classList.remove("hidden");
  inspectorStatusBadge.textContent = success ? "Success" : "Notice";
  inspectorStatusBadge.className = success ? "badge-success" : "badge-error";
  intentName.textContent = intent;
  intentConfidence.textContent = `${(confidence * 100).toFixed(1)}%`;
  entityTagsContainer.innerHTML = `<span style="font-size:0.75rem; color:#94a3b8;">None</span>`;
  planStepsList.innerHTML = "";
  agentMessageBanner.textContent = message;
}

// ---------------- REST Tasks API ----------------

async function fetchTasks() {
  try {
    const res = await fetch(`${API_BASE}/tasks`);
    allTasks = await res.json();
    renderTasks();
  } catch (err) {
    console.error("Error fetching tasks:", err);
  }
}

async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    const stats = await res.json();
    metricTotal.textContent = stats.total;
    metricPending.textContent = stats.pending;
    metricCompleted.textContent = stats.completed;
    metricHigh.textContent = stats.high_priority;
  } catch (err) {
    console.error("Error fetching stats:", err);
  }
}

function renderTasks() {
  tasksGrid.innerHTML = "";

  const filtered = allTasks.filter((task) => {
    // Status Filter
    if (activeStatusFilter && task.status !== activeStatusFilter) {
      return false;
    }
    // Priority Filter
    if (activePriorityFilter && task.priority !== activePriorityFilter) {
      return false;
    }
    // Search Query
    if (activeSearchQuery) {
      const matchTitle = (task.title || "").toLowerCase().includes(activeSearchQuery);
      const matchDesc = (task.description || "").toLowerCase().includes(activeSearchQuery);
      const matchCat = (task.category || "").toLowerCase().includes(activeSearchQuery);
      if (!matchTitle && !matchDesc && !matchCat) return false;
    }
    return true;
  });

  taskCountSubtitle.textContent = `${filtered.length} task${filtered.length === 1 ? "" : "s"}`;

  if (filtered.length === 0) {
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  filtered.forEach((task) => {
    const card = document.createElement("div");
    card.className = `task-card ${task.status === "Completed" ? "completed" : ""}`;
    card.id = `task-card-${task.id}`;

    const isCompleted = task.status === "Completed";
    const priorityClass = (task.priority || "Medium").toLowerCase();

    card.innerHTML = `
      <div class="task-card-top">
        <input 
          type="checkbox" 
          class="task-checkbox" 
          ${isCompleted ? "checked" : ""}
          title="Toggle completion"
        >
        <div class="task-main-content">
          <div class="task-title-row">
            <span class="task-id-badge">#${task.id}</span>
            <span class="task-title">${escapeHtml(task.title)}</span>
          </div>
          ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ""}
          <div class="task-meta-row">
            <span class="priority-badge ${priorityClass}">${task.priority}</span>
            <span class="category-pill">${escapeHtml(task.category || "General")}</span>
            ${task.deadline ? `<span class="deadline-badge">📅 ${task.deadline}</span>` : ""}
          </div>
        </div>
      </div>
      <div class="task-card-actions">
        <button class="btn-card-action edit-btn">Edit</button>
        <button class="btn-card-action delete delete-btn">Delete</button>
      </div>
    `;

    // Inline Status Checkbox
    const checkbox = card.querySelector(".task-checkbox");
    checkbox.addEventListener("change", async () => {
      const newStatus = checkbox.checked ? "Completed" : "Pending";
      await toggleTaskStatus(task.id, newStatus);
    });

    // Edit Button
    const editBtn = card.querySelector(".edit-btn");
    editBtn.addEventListener("click", () => openModal(task));

    // Delete Button
    const deleteBtn = card.querySelector(".delete-btn");
    deleteBtn.addEventListener("click", () => deleteTask(task.id));

    tasksGrid.appendChild(card);
  });
}

async function toggleTaskStatus(taskId, newStatus) {
  try {
    await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    await fetchTasks();
    await fetchStats();
  } catch (err) {
    console.error("Failed to toggle task status:", err);
  }
}

async function deleteTask(taskId) {
  if (!confirm(`Are you sure you want to delete Task #${taskId}?`)) return;
  try {
    await fetch(`${API_BASE}/tasks/${taskId}`, { method: "DELETE" });
    await fetchTasks();
    await fetchStats();
  } catch (err) {
    console.error("Failed to delete task:", err);
  }
}

// ---------------- Modal Management ----------------

function openModal(task = null) {
  taskModal.classList.remove("hidden");
  if (task) {
    modalTitle.textContent = `Edit Task #${task.id}`;
    formTaskId.value = task.id;
    formTitle.value = task.title;
    formDescription.value = task.description || "";
    formPriority.value = task.priority || "Medium";
    formCategory.value = task.category || "General";
    formDeadline.value = task.deadline || "";
    formStatus.value = task.status || "Pending";
  } else {
    modalTitle.textContent = "Create New Task";
    formTaskId.value = "";
    taskForm.reset();
    formPriority.value = "Medium";
    formStatus.value = "Pending";
    formCategory.value = "General";
  }
  formTitle.focus();
}

function closeModal() {
  taskModal.classList.add("hidden");
}

async function handleFormSubmit(e) {
  e.preventDefault();
  const id = formTaskId.value;
  const payload = {
    title: formTitle.value.trim(),
    description: formDescription.value.trim(),
    priority: formPriority.value,
    category: formCategory.value.trim() || "General",
    deadline: formDeadline.value || null,
    status: formStatus.value,
  };

  try {
    if (id) {
      // Update
      await fetch(`${API_BASE}/tasks/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      // Create
      await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    closeModal();
    await fetchTasks();
    await fetchStats();
  } catch (err) {
    console.error("Error saving task:", err);
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
}
