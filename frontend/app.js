/* ==========================================================================
   TaskForge — Interactive Frontend Controller
   ========================================================================== */

const API_BASE = "";

// State
let allTasks = [];
let activeStatusFilter = "";
let activePriorityFilter = "";
let activeCategoryFilter = "";
let activeSearchQuery = "";
let currentAnalyticsRange = "7d";
let activeTab = "tasks";

// Chart.js Instances
let completionTrendChartInstance = null;
let statusDistributionChartInstance = null;
let priorityDistributionChartInstance = null;
let categoryDistributionChartInstance = null;

// DOM Elements — Header & Navigation
const tabTasksBtn = document.getElementById("tabTasksBtn");
const tabAnalyticsBtn = document.getElementById("tabAnalyticsBtn");
const tasksView = document.getElementById("tasksView");
const analyticsView = document.getElementById("analyticsView");
const resetMemoryBtn = document.getElementById("resetMemoryBtn");

// DOM Elements — AI Natural Language Command Center
const agentCommandInput = document.getElementById("agentCommandInput");
const agentExecuteBtn = document.getElementById("agentExecuteBtn");
const aiInspector = document.getElementById("aiInspector");
const intentName = document.getElementById("intentName");
const intentConfidence = document.getElementById("intentConfidence");
const entityTagsContainer = document.getElementById("entityTagsContainer");
const planStepsList = document.getElementById("planStepsList");
const agentMessageBanner = document.getElementById("agentMessageBanner");
const inspectorStatusBadge = document.getElementById("inspectorStatusBadge");

// DOM Elements — Workspace Metrics
const metricTotal = document.getElementById("metricTotal");
const metricPending = document.getElementById("metricPending");
const metricCompleted = document.getElementById("metricCompleted");
const metricHigh = document.getElementById("metricHigh");

// DOM Elements — Task Management
const tasksGrid = document.getElementById("tasksGrid");
const emptyState = document.getElementById("emptyState");
const taskCountSubtitle = document.getElementById("taskCountSubtitle");
const taskSearchInput = document.getElementById("taskSearchInput");
const statusFilterButtons = document.querySelectorAll(".filter-btn");
const priorityFilterSelect = document.getElementById("priorityFilterSelect");
const activeCategoryContainer = document.getElementById("activeCategoryContainer");
const activeCategoryText = document.getElementById("activeCategoryText");
const clearCategoryFilterBtn = document.getElementById("clearCategoryFilterBtn");

// DOM Elements — Task Modal
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

// DOM Elements — Analytics KPI Summary
const kpiTotalTasks = document.getElementById("kpiTotalTasks");
const kpiCompletedTasks = document.getElementById("kpiCompletedTasks");
const kpiCompletionRate = document.getElementById("kpiCompletionRate");
const kpiPendingTasks = document.getElementById("kpiPendingTasks");
const kpiOverdueTasks = document.getElementById("kpiOverdueTasks");
const kpiOverdueBadge = document.getElementById("kpiOverdueBadge");
const kpiDateSpan = document.getElementById("kpiDateSpan");
const analyticsLoading = document.getElementById("analyticsLoading");
const dateRangeSelector = document.getElementById("dateRangeSelector");

// DOM Elements — Chart Badges & Footers
const trendTotalBadge = document.getElementById("trendTotalBadge");
const trendEmptyState = document.getElementById("trendEmptyState");
const statusEmptyState = document.getElementById("statusEmptyState");
const overdueFooterBadge = document.getElementById("overdueFooterBadge");
const overdueFooterText = document.getElementById("overdueFooterText");
const priorityEmptyState = document.getElementById("priorityEmptyState");
const categoryEmptyState = document.getElementById("categoryEmptyState");

// Register Chart.js Center Text Plugin for Doughnut Chart
if (typeof Chart !== "undefined") {
  const centerTextPlugin = {
    id: "centerTextPlugin",
    afterDraw(chart) {
      if (chart.config.type !== "doughnut") return;
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      const { top, bottom, left, right } = chartArea;
      ctx.save();
      const dataset = chart.data.datasets[0];
      const total = dataset && dataset.data ? dataset.data.reduce((a, b) => a + (Number(b) || 0), 0) : 0;
      const centerX = (left + right) / 2;
      const centerY = (top + bottom) / 2;

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      // Count
      ctx.fillStyle = "#0f172a";
      ctx.font = "700 24px 'Plus Jakarta Sans', sans-serif";
      ctx.fillText(total.toString(), centerX, centerY - 9);

      // Label
      ctx.fillStyle = "#64748b";
      ctx.font = "600 10px 'Plus Jakarta Sans', sans-serif";
      ctx.letterSpacing = "0.05em";
      ctx.fillText("TOTAL TASKS", centerX, centerY + 13);
      ctx.restore();
    },
  };
  Chart.register(centerTextPlugin);
}

// ---------------- Initialization ----------------

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchTasks();
  fetchStats();
});

function initEventListeners() {
  // Navigation Tabs
  if (tabTasksBtn) tabTasksBtn.addEventListener("click", () => switchTab("tasks"));
  if (tabAnalyticsBtn) tabAnalyticsBtn.addEventListener("click", () => switchTab("analytics"));

  // AI Command Execution
  if (agentExecuteBtn) agentExecuteBtn.addEventListener("click", handleAgentExecute);
  if (agentCommandInput) {
    agentCommandInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleAgentExecute();
    });
  }

  // Suggestion Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const cmd = chip.getAttribute("data-cmd");
      if (cmd && agentCommandInput) {
        agentCommandInput.value = cmd;
        handleAgentExecute();
      }
    });
  });

  // Reset Context Memory
  if (resetMemoryBtn) resetMemoryBtn.addEventListener("click", handleResetContext);

  // Task Search
  if (taskSearchInput) {
    taskSearchInput.addEventListener("input", (e) => {
      activeSearchQuery = e.target.value.trim().toLowerCase();
      renderTasks();
    });
  }

  // Status Filter Buttons
  statusFilterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      statusFilterButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeStatusFilter = btn.getAttribute("data-status") || "";
      renderTasks();
    });
  });

  // Priority Filter Select
  if (priorityFilterSelect) {
    priorityFilterSelect.addEventListener("change", (e) => {
      activePriorityFilter = e.target.value;
      renderTasks();
    });
  }

  // Clear Category Filter Button
  if (clearCategoryFilterBtn) {
    clearCategoryFilterBtn.addEventListener("click", () => {
      clearCategoryFilter();
    });
  }

  // Modal Open/Close
  if (openCreateModalBtn) openCreateModalBtn.addEventListener("click", () => openModal());
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeModal);
  if (cancelModalBtn) cancelModalBtn.addEventListener("click", closeModal);
  if (taskForm) taskForm.addEventListener("submit", handleFormSubmit);

  // Close modal when clicking on dark overlay backdrop
  if (taskModal) {
    taskModal.addEventListener("click", (e) => {
      if (e.target === taskModal) closeModal();
    });
  }

  // Date Range Selector in Analytics View
  if (dateRangeSelector) {
    dateRangeSelector.querySelectorAll(".range-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        dateRangeSelector.querySelectorAll(".range-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentAnalyticsRange = btn.getAttribute("data-range") || "7d";
        fetchAnalytics(currentAnalyticsRange);
      });
    });
  }
}

// ---------------- Tab Switching ----------------

function switchTab(tab) {
  activeTab = tab;
  if (tab === "tasks") {
    tabTasksBtn.classList.add("active");
    tabAnalyticsBtn.classList.remove("active");
    tasksView.classList.remove("hidden");
    analyticsView.classList.add("hidden");
  } else if (tab === "analytics") {
    tabAnalyticsBtn.classList.add("active");
    tabTasksBtn.classList.remove("active");
    analyticsView.classList.remove("hidden");
    tasksView.classList.add("hidden");
    fetchAnalytics(currentAnalyticsRange);
  }
}

// ---------------- AI Agent Natural Language Execution ----------------

async function handleAgentExecute() {
  const goal = agentCommandInput.value.trim();
  if (!goal) return;

  agentExecuteBtn.disabled = true;
  agentExecuteBtn.innerHTML = `<span>Thinking...</span>`;

  try {
    const res = await fetch(`${API_BASE}/agent/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal: goal }),
    });

    const result = await res.json();
    renderAIInspector(result);

    // Refresh application state
    await fetchTasks();
    await fetchStats();
    if (activeTab === "analytics" || !analyticsView.classList.contains("hidden")) {
      await fetchAnalytics(currentAnalyticsRange);
    }
  } catch (err) {
    console.error("Agent execution failed:", err);
    showInspectorFeedback("Error", "FAILED", 0.0, {}, [], "Execution failed. Server unreachable.", false);
  } finally {
    agentExecuteBtn.disabled = false;
    agentExecuteBtn.innerHTML = `
      <span>Execute</span>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
      </svg>
    `;
  }
}

async function handleResetContext() {
  try {
    const res = await fetch(`${API_BASE}/agent/context/reset`, { method: "POST" });
    const data = await res.json();
    alert("Conversational context memory has been reset.");
    if (aiInspector) aiInspector.classList.add("hidden");
  } catch (err) {
    console.error("Context reset error:", err);
  }
}

function renderAIInspector(result) {
  aiInspector.classList.remove("hidden");
  const success = result.success;

  // Status Badge
  inspectorStatusBadge.textContent = success ? "Success" : "Refused / Unknown";
  inspectorStatusBadge.className = success ? "badge-success" : "badge-error";

  // Intent & Confidence
  intentName.textContent = result.intent || "UNKNOWN";
  intentConfidence.textContent = `${((result.confidence || 0) * 100).toFixed(1)}%`;

  // NER Entities
  entityTagsContainer.innerHTML = "";
  const rawEntities = (result.plan && result.plan.extracted_entities) || {};
  const entries = Object.entries(rawEntities);
  if (entries.length === 0) {
    entityTagsContainer.innerHTML = `<span style="font-size:0.75rem; color:#94a3b8;">No entities extracted</span>`;
  } else {
    entries.forEach(([key, val]) => {
      if (val !== null && val !== undefined) {
        const tag = document.createElement("span");
        tag.className = "entity-tag";
        tag.innerHTML = `<strong>${escapeHtml(key)}:</strong> ${escapeHtml(String(val))}`;
        entityTagsContainer.appendChild(tag);
      }
    });
  }

  // Plan Steps
  planStepsList.innerHTML = "";
  const steps = (result.plan && result.plan.steps) || [];
  if (steps.length > 0) {
    steps.forEach((step) => {
      const li = document.createElement("li");
      li.className = "plan-step-item";
      li.innerHTML = `
        <span class="step-num">${step.step_number}</span>
        <div class="step-details">
          <span class="step-action">${escapeHtml(step.action)}</span>
          <span class="step-desc">${escapeHtml(step.description)}</span>
        </div>
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

// ---------------- REST Tasks API & Workspace ----------------

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
    // Category Filter
    if (activeCategoryFilter) {
      const taskCat = (task.category || "General").toLowerCase();
      if (taskCat !== activeCategoryFilter.toLowerCase()) {
        return false;
      }
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
    const priorityKey = (task.priority || "Medium").toLowerCase().replace(/\s+/g, "-");

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
            <span class="priority-badge ${priorityKey}">${escapeHtml(task.priority)}</span>
            <span class="category-pill">${escapeHtml(task.category || "General")}</span>
            ${task.deadline ? `<span class="deadline-badge">📅 ${escapeHtml(task.deadline)}</span>` : ""}
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
    if (activeTab === "analytics" || !analyticsView.classList.contains("hidden")) {
      await fetchAnalytics(currentAnalyticsRange);
    }
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
    if (activeTab === "analytics" || !analyticsView.classList.contains("hidden")) {
      await fetchAnalytics(currentAnalyticsRange);
    }
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
      await fetch(`${API_BASE}/tasks/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    closeModal();
    await fetchTasks();
    await fetchStats();
    if (activeTab === "analytics" || !analyticsView.classList.contains("hidden")) {
      await fetchAnalytics(currentAnalyticsRange);
    }
  } catch (err) {
    console.error("Error saving task:", err);
  }
}

// ---------------- Interactive Filtering Handlers (From Charts) ----------------

function filterByStatus(status) {
  activeStatusFilter = status;
  statusFilterButtons.forEach((btn) => {
    const s = btn.getAttribute("data-status") || "";
    btn.classList.toggle("active", s === status);
  });
  switchTab("tasks");
  renderTasks();
  scrollToTasks();
}

function filterByPriority(priority) {
  activePriorityFilter = priority;
  if (priorityFilterSelect) priorityFilterSelect.value = priority;
  switchTab("tasks");
  renderTasks();
  scrollToTasks();
}

function filterByCategory(category) {
  activeCategoryFilter = category;
  if (activeCategoryContainer && activeCategoryText) {
    activeCategoryText.textContent = category;
    activeCategoryContainer.classList.remove("hidden");
  }
  switchTab("tasks");
  renderTasks();
  scrollToTasks();
}

function clearCategoryFilter() {
  activeCategoryFilter = "";
  if (activeCategoryContainer) activeCategoryContainer.classList.add("hidden");
  renderTasks();
}

function scrollToTasks() {
  const section = document.querySelector(".task-section");
  if (section) section.scrollIntoView({ behavior: "smooth" });
}

// ==========================================================================
// Analytics Dashboard Controller (4 Interactive Charts)
// ==========================================================================

async function fetchAnalytics(range = "7d") {
  if (analyticsLoading) analyticsLoading.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/analytics/overview?range=${range}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // 1. Update KPI Strip
    updateKPIs(data);

    // 2. Render Chart 1: Weekly Task Completion (Line Chart)
    renderCompletionTrendChart(data.completion_trend);

    // 3. Render Chart 2: Task Status Distribution (Doughnut Chart)
    renderStatusDistributionChart(data.status_distribution);

    // 4. Render Chart 3: Priority Distribution (Horizontal Bar Chart)
    renderPriorityDistributionChart(data.priority_distribution);

    // 5. Render Chart 4: Category-wise Task Distribution (Pie Chart)
    renderCategoryDistributionChart(data.category_distribution);
  } catch (err) {
    console.error("Error loading analytics:", err);
  } finally {
    if (analyticsLoading) analyticsLoading.classList.add("hidden");
  }
}

function updateKPIs(data) {
  const s = data.summary;
  if (kpiTotalTasks) kpiTotalTasks.textContent = s.total_tasks;
  if (kpiCompletedTasks) kpiCompletedTasks.textContent = s.completed_tasks;
  if (kpiCompletionRate) kpiCompletionRate.textContent = `${s.completion_rate.toFixed(1)}% rate`;
  if (kpiPendingTasks) kpiPendingTasks.textContent = s.pending_tasks;
  if (kpiOverdueTasks) kpiOverdueTasks.textContent = s.overdue_tasks;

  if (kpiOverdueBadge) {
    if (s.overdue_tasks > 0) {
      kpiOverdueBadge.textContent = `${s.overdue_tasks} action required`;
      kpiOverdueBadge.className = "kpi-badge badge-danger";
    } else {
      kpiOverdueBadge.textContent = "On track";
      kpiOverdueBadge.className = "kpi-badge badge-neutral";
    }
  }

  if (kpiDateSpan) {
    const dr = data.date_range;
    if (dr.range === "all") {
      kpiDateSpan.textContent = "All recorded history";
    } else if (dr.start_date && dr.end_date) {
      kpiDateSpan.textContent = `${dr.start_date} → ${dr.end_date}`;
    }
  }
}

// ---------------- Chart 1: Weekly Task Completion (Line Chart) ----------------

function renderCompletionTrendChart(trendPoints) {
  const canvas = document.getElementById("completionTrendChart");
  if (!canvas) return;

  const totalCompleted = trendPoints.reduce((acc, pt) => acc + pt.completed_count, 0);
  if (trendTotalBadge) trendTotalBadge.textContent = `${totalCompleted} completed`;

  if (trendEmptyState) {
    trendEmptyState.classList.toggle("hidden", totalCompleted > 0 || trendPoints.length > 0);
  }

  const labels = trendPoints.map((pt) => pt.label);
  const data = trendPoints.map((pt) => pt.completed_count);

  if (completionTrendChartInstance) {
    completionTrendChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");

  // Subtle gradient fill under the line
  const gradient = ctx.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, "rgba(37, 99, 235, 0.22)");
  gradient.addColorStop(1, "rgba(37, 99, 235, 0.0)");

  completionTrendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Completed Tasks",
          data: data,
          borderColor: "#2563eb",
          backgroundColor: gradient,
          borderWidth: 2.5,
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: "#2563eb",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          pointHoverBackgroundColor: "#1d4ed8",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f172a",
          titleFont: { family: "'Plus Jakarta Sans'", size: 12, weight: "bold" },
          bodyFont: { family: "'Plus Jakarta Sans'", size: 12 },
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex;
              const pt = trendPoints[idx];
              return `${pt.label} (${pt.day_name}) — ${pt.date}`;
            },
            label: (item) => `Completed tasks: ${item.parsed.y}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: "'Plus Jakarta Sans'", size: 11 },
            color: "#64748b",
            maxRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: "#f1f5f9" },
          ticks: {
            precision: 0,
            stepSize: 1,
            font: { family: "'Plus Jakarta Sans'", size: 11 },
            color: "#64748b",
          },
        },
      },
    },
  });
}

// ---------------- Chart 2: Task Status Distribution (Doughnut Chart) ----------------

function renderStatusDistributionChart(statusData) {
  const canvas = document.getElementById("statusDistributionChart");
  if (!canvas) return;

  const total = statusData.total;
  if (statusEmptyState) {
    statusEmptyState.classList.toggle("hidden", total > 0);
  }

  // Update Overdue Footer
  if (overdueFooterText) {
    overdueFooterText.textContent = `${statusData.overdue} task${statusData.overdue === 1 ? "" : "s"} overdue`;
  }
  if (overdueFooterBadge) {
    overdueFooterBadge.style.display = statusData.overdue > 0 ? "inline-flex" : "none";
  }

  const pending = statusData.pending;
  const completed = statusData.completed;

  if (statusDistributionChartInstance) {
    statusDistributionChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");

  statusDistributionChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Pending", "Completed"],
      datasets: [
        {
          data: total > 0 ? [pending, completed] : [0, 0],
          backgroundColor: ["#f59e0b", "#10b981"],
          hoverBackgroundColor: ["#d97706", "#059669"],
          borderWidth: 3,
          borderColor: "#ffffff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      onClick: (event, elements) => {
        if (elements && elements.length > 0) {
          const idx = elements[0].index;
          const status = idx === 0 ? "Pending" : "Completed";
          filterByStatus(status);
        }
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            font: { family: "'Plus Jakarta Sans'", size: 12, weight: "600" },
            color: "#334155",
            usePointStyle: true,
            padding: 16,
            generateLabels: (chart) => {
              const data = chart.data;
              return data.labels.map((label, i) => {
                const val = data.datasets[0].data[i];
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
                return {
                  text: `${label}: ${val} (${pct}%)`,
                  fillStyle: data.datasets[0].backgroundColor[i],
                  strokeStyle: "#ffffff",
                  lineWidth: 1,
                  hidden: false,
                  index: i,
                };
              });
            },
          },
        },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: (item) => {
              const label = item.label || "";
              const val = item.raw || 0;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
              return ` ${label}: ${val} tasks (${pct}%)`;
            },
          },
        },
      },
    },
  });
}

// ---------------- Chart 3: Priority Distribution (Horizontal Bar Chart) ----------------

function renderPriorityDistributionChart(priorityPoints) {
  const canvas = document.getElementById("priorityDistributionChart");
  if (!canvas) return;

  const total = priorityPoints.reduce((acc, p) => acc + p.count, 0);
  if (priorityEmptyState) {
    priorityEmptyState.classList.toggle("hidden", total > 0);
  }

  const labels = priorityPoints.map((p) => p.priority);
  const counts = priorityPoints.map((p) => p.count);

  const colors = {
    Critical: "#e11d48",
    High: "#ea580c",
    Medium: "#2563eb",
    Low: "#64748b",
    "Very Low": "#94a3b8",
  };

  const bgColors = labels.map((lbl) => colors[lbl] || "#2563eb");

  if (priorityDistributionChartInstance) {
    priorityDistributionChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");

  priorityDistributionChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Tasks",
          data: counts,
          backgroundColor: bgColors,
          borderRadius: 6,
          barThickness: 20,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      onClick: (event, elements) => {
        if (elements && elements.length > 0) {
          const idx = elements[0].index;
          const prio = labels[idx];
          filterByPriority(prio);
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: (item) => {
              const count = item.parsed.x;
              const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
              return ` ${count} tasks (${pct}%)`;
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: "#f1f5f9" },
          ticks: {
            precision: 0,
            stepSize: 1,
            font: { family: "'Plus Jakarta Sans'", size: 11 },
            color: "#64748b",
          },
        },
        y: {
          grid: { display: false },
          ticks: {
            font: { family: "'Plus Jakarta Sans'", size: 12, weight: "600" },
            color: "#334155",
          },
        },
      },
    },
  });
}

// ---------------- Chart 4: Category-wise Task Distribution (Pie Chart) ----------------

function renderCategoryDistributionChart(categoryPoints) {
  const canvas = document.getElementById("categoryDistributionChart");
  if (!canvas) return;

  const total = categoryPoints.reduce((acc, c) => acc + c.count, 0);
  if (categoryEmptyState) {
    categoryEmptyState.classList.toggle("hidden", categoryPoints.length > 0);
  }

  const labels = categoryPoints.map((c) => c.category);
  const counts = categoryPoints.map((c) => c.count);

  const palette = [
    "#2563eb",
    "#8b5cf6",
    "#06b6d4",
    "#10b981",
    "#f59e0b",
    "#ec4899",
    "#f97316",
    "#6366f1",
    "#14b8a6",
    "#84cc16",
  ];
  const bgColors = labels.map((_, i) => palette[i % palette.length]);

  if (categoryDistributionChartInstance) {
    categoryDistributionChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");

  categoryDistributionChartInstance = new Chart(ctx, {
    type: "pie",
    data: {
      labels: labels,
      datasets: [
        {
          data: counts,
          backgroundColor: bgColors,
          borderWidth: 2,
          borderColor: "#ffffff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (event, elements) => {
        if (elements && elements.length > 0) {
          const idx = elements[0].index;
          const cat = labels[idx];
          filterByCategory(cat);
        }
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            font: { family: "'Plus Jakarta Sans'", size: 11, weight: "500" },
            color: "#334155",
            usePointStyle: true,
            padding: 12,
            generateLabels: (chart) => {
              const data = chart.data;
              return data.labels.map((label, i) => {
                const val = data.datasets[0].data[i];
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
                return {
                  text: `${label}: ${val} (${pct}%)`,
                  fillStyle: data.datasets[0].backgroundColor[i],
                  strokeStyle: "#ffffff",
                  lineWidth: 1,
                  hidden: false,
                  index: i,
                };
              });
            },
          },
        },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: (item) => {
              const label = item.label || "";
              const val = item.raw || 0;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
              return ` ${label}: ${val} tasks (${pct}%)`;
            },
          },
        },
      },
    },
  });
}

function escapeHtml(text) {
  if (!text) return "";
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
}
