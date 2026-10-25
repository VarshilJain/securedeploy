/**
 * SecureDeploy ML - Frontend Client Logic
 * Financial News Sentiment Classifier & DevSecOps Monitor
 * Pure Vanilla JavaScript (No external frameworks)
 */

document.addEventListener("DOMContentLoaded", () => {
  // -------------------------------------------------------------
  // State Management (Session Memory Only, No localStorage)
  // -------------------------------------------------------------
  const sessionHistory = [];
  const MAX_HISTORY = 5;

  // DOM Elements - Navigation
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");

  // DOM Elements - Health Badge
  const apiStatusDot = document.getElementById("api-status-dot");
  const apiStatusText = document.getElementById("api-status-text");

  // DOM Elements - Classifier
  const sentimentForm = document.getElementById("sentiment-form");
  const headlineInput = document.getElementById("headline-input");
  const charCounter = document.getElementById("char-count-desc");
  const validationError = document.getElementById("validation-error");
  const analyzeBtn = document.getElementById("analyze-btn");
  const analyzeSpinner = document.getElementById("analyze-spinner");
  const analyzeBtnText = document.getElementById("analyze-btn-text");
  const clearBtn = document.getElementById("clear-btn");
  const exampleChips = document.querySelectorAll(".chip-btn");

  // DOM Elements - Results
  const resultEmpty = document.getElementById("result-empty");
  const resultContent = document.getElementById("result-content");
  const resultBadge = document.getElementById("result-badge");
  const resultConfidence = document.getElementById("result-confidence");
  const resultConfidenceBar = document.getElementById("result-confidence-bar");
  const probPositive = document.getElementById("prob-positive");
  const probNeutral = document.getElementById("prob-neutral");
  const probNegative = document.getElementById("prob-negative");
  const barPos = document.getElementById("bar-pos");
  const barNeu = document.getElementById("bar-neu");
  const barNeg = document.getElementById("bar-neg");
  const historyList = document.getElementById("history-list");

  // DOM Elements - DevSecOps Status
  const refreshPipelineBtn = document.getElementById("refresh-pipeline-btn");
  const pipelineNoticeBanner = document.getElementById("pipeline-notice-banner");
  const pipelineNoticeText = document.getElementById("pipeline-notice-text");
  const pipelineRepoName = document.getElementById("pipeline-repo-name");
  const pipelineLastChecked = document.getElementById("pipeline-last-checked");
  const pipelineCacheTag = document.getElementById("pipeline-cache-tag");

  // -------------------------------------------------------------
  // Navigation Tabs Switching
  // -------------------------------------------------------------
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");

      tabButtons.forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      tabContents.forEach((c) => {
        c.classList.remove("active");
        c.hidden = true;
      });

      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      const activeContent = document.getElementById(targetId);
      if (activeContent) {
        activeContent.classList.add("active");
        activeContent.hidden = false;
      }

      // If DevSecOps tab clicked, auto-fetch status
      if (targetId === "section-devsecops") {
        fetchPipelineStatus();
      }
    });
  });

  // -------------------------------------------------------------
  // API Health Check
  // -------------------------------------------------------------
  async function checkApiHealth() {
    try {
      const response = await fetch("/health");
      const data = await response.json();
      if (response.ok && data.status === "ok" && data.model_loaded) {
        apiStatusDot.className = "status-dot status-healthy";
        apiStatusText.textContent = "API: Healthy (Model Loaded)";
      } else {
        apiStatusDot.className = "status-dot status-unavailable";
        apiStatusText.textContent = "API: Degraded (Model Missing)";
      }
    } catch (err) {
      apiStatusDot.className = "status-dot status-unavailable";
      apiStatusText.textContent = "API: Offline";
    }
  }

  // -------------------------------------------------------------
  // Input Validation & Character Counter
  // -------------------------------------------------------------
  function updateCharacterCount() {
    const length = headlineInput.value.length;
    charCounter.textContent = `${length} / 500 characters`;

    if (length > 0 && length < 3) {
      validationError.textContent = "Headline must be at least 3 characters long.";
      headlineInput.classList.add("input-error");
    } else {
      validationError.textContent = "";
      headlineInput.classList.remove("input-error");
    }
  }

  headlineInput.addEventListener("input", updateCharacterCount);

  // Example Headline Chips
  exampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const text = chip.getAttribute("data-text");
      headlineInput.value = text;
      updateCharacterCount();
      headlineInput.focus();
    });
  });

  // Clear Form
  clearBtn.addEventListener("click", () => {
    headlineInput.value = "";
    updateCharacterCount();
    headlineInput.focus();
  });

  // -------------------------------------------------------------
  // Predict Form Submission
  // -------------------------------------------------------------
  sentimentForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    const text = headlineInput.value.trim();

    // Client-side validation
    if (!text || text.length < 3) {
      validationError.textContent = "Please enter a headline with at least 3 characters.";
      headlineInput.classList.add("input-error");
      headlineInput.focus();
      return;
    }

    if (text.length > 500) {
      validationError.textContent = "Headline cannot exceed 500 characters.";
      headlineInput.classList.add("input-error");
      headlineInput.focus();
      return;
    }

    validationError.textContent = "";
    headlineInput.classList.remove("input-error");

    // Loading State
    analyzeBtn.disabled = true;
    analyzeSpinner.hidden = false;
    analyzeBtnText.textContent = "Analyzing...";

    try {
      const response = await fetch("/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error ${response.status}`);
      }

      displayResult(text, data);
    } catch (err) {
      validationError.textContent = `Inference failed: ${err.message}`;
      headlineInput.classList.add("input-error");
    } finally {
      analyzeBtn.disabled = false;
      analyzeSpinner.hidden = true;
      analyzeBtnText.textContent = "Analyze Sentiment";
    }
  });

  function displayResult(text, data) {
    resultEmpty.hidden = true;
    resultContent.hidden = false;

    const label = data.label.toLowerCase();
    const confPct = (data.confidence * 100).toFixed(2);

    // Set badge style
    resultBadge.textContent = label.toUpperCase();
    resultBadge.className = `badge badge-${label}`;
    resultConfidence.textContent = `${confPct}%`;

    resultConfidenceBar.style.width = `${confPct}%`;
    resultConfidenceBar.setAttribute("aria-valuenow", confPct);

    // Set per-class probabilities
    const probs = data.probabilities || {};
    const posPct = ((probs.positive || 0) * 100).toFixed(2);
    const neuPct = ((probs.neutral || 0) * 100).toFixed(2);
    const negPct = ((probs.negative || 0) * 100).toFixed(2);

    probPositive.textContent = `${posPct}%`;
    probNeutral.textContent = `${neuPct}%`;
    probNegative.textContent = `${negPct}%`;

    barPos.style.width = `${posPct}%`;
    barNeu.style.width = `${neuPct}%`;
    barNeg.style.width = `${negPct}%`;

    // Record in Session Memory History
    sessionHistory.unshift({
      text,
      label,
      confidence: confPct,
      time: new Date().toLocaleTimeString(),
    });

    if (sessionHistory.length > MAX_HISTORY) {
      sessionHistory.pop();
    }

    renderHistory();
  }

  function renderHistory() {
    historyList.innerHTML = "";
    sessionHistory.forEach((item) => {
      const li = document.createElement("li");
      li.className = "history-item";
      li.innerHTML = `
        <span class="history-text" title="${item.text}">${item.text}</span>
        <span class="badge badge-${item.label}" style="font-size:0.7rem; padding: 0.15rem 0.4rem;">
          ${item.label.toUpperCase()} (${item.confidence}%)
        </span>
      `;
      historyList.appendChild(li);
    });
  }

  // -------------------------------------------------------------
  // DevSecOps Pipeline Status Fetcher
  // -------------------------------------------------------------
  async function fetchPipelineStatus() {
    refreshPipelineBtn.disabled = true;
    refreshPipelineBtn.textContent = "Checking...";

    try {
      const response = await fetch("/api/pipeline-status");
      const data = await response.json();

      pipelineLastChecked.textContent = new Date().toLocaleTimeString();
      pipelineCacheTag.hidden = !data.cached;

      if (!data.configured) {
        pipelineNoticeBanner.className = "alert-box alert-warning";
        pipelineNoticeText.textContent =
          "Local Standalone Mode: GITHUB_REPOSITORY is unset. Statuses will remain UNKNOWN until deployed to GitHub with Actions.";
        pipelineRepoName.textContent = "Local / Not configured";
      } else {
        pipelineNoticeBanner.className = "alert-box alert-info";
        pipelineNoticeText.textContent = data.message || "Connected to GitHub Actions.";
        pipelineRepoName.textContent = data.repository || "Configured";
      }

      // Update individual status cards
      const jobs = data.jobs || {};
      const jobKeys = [
        "unit_tests",
        "docker_build",
        "trivy",
        "checkov",
        "gitleaks",
        "pipeline",
        "ghcr_publish",
      ];

      jobKeys.forEach((key) => {
        const status = (jobs[key] || "unknown").toLowerCase();
        const pill = document.getElementById(`pill-${key}`);
        if (pill) {
          pill.className = `status-pill status-${status}`;
          pill.textContent = status.toUpperCase().replace("_", " ");
        }
      });
    } catch (err) {
      pipelineNoticeBanner.className = "alert-box alert-warning";
      pipelineNoticeText.textContent = `Failed to query pipeline status: ${err.message}`;
    } finally {
      refreshPipelineBtn.disabled = false;
      refreshPipelineBtn.textContent = "\u21BB Refresh Status";
    }
  }

  refreshPipelineBtn.addEventListener("click", fetchPipelineStatus);

  // Initialize
  checkApiHealth();
});
