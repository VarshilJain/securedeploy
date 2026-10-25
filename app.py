"""
SecureDeploy ML - Financial News Sentiment Classifier
Flask Web Application & REST API
Cloud Computing Lab DJS23ALMD701
"""

import os
import sys
import time
from typing import Any, Dict, Optional, Tuple
from flask import Flask, jsonify, render_template, request, Response
import joblib
import requests

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")


class PipelineStatusCache:
    """In-memory cache for GitHub Actions pipeline status (TTL: 60 seconds)."""

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self.last_fetched: float = 0.0
        self.cached_data: Optional[Dict[str, Any]] = None

    def get(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        if self.cached_data and (now - self.last_fetched < self.ttl_seconds):
            return self.cached_data
        return None

    def set(self, data: Dict[str, Any]) -> None:
        self.last_fetched = time.time()
        self.cached_data = data


def map_conclusion(conclusion: Optional[str], status: Optional[str]) -> str:
    """Maps GitHub job conclusion and status to strict frontend status enum."""
    if conclusion == "success":
        return "passed"
    if conclusion in ("failure", "timed_out", "cancelled", "action_required"):
        return "failed"
    if status in ("queued", "in_progress", "waiting", "requested"):
        return "not_run"
    if conclusion == "skipped":
        return "not_run"
    return "unknown"


def fetch_github_pipeline_status(
    repo: str, token: Optional[str] = None
) -> Dict[str, Any]:
    """Queries GitHub REST API for devsecops.yml workflow status with 5s timeout."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SecureDeploy-ML-Monitor",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base_url = f"https://api.github.com/repos/{repo}"
    workflow_url = f"{base_url}/actions/workflows/devsecops.yml/runs?per_page=1"

    default_jobs = {
        "unit_tests": "unknown",
        "docker_build": "unknown",
        "trivy": "unknown",
        "checkov": "unknown",
        "gitleaks": "unknown",
        "pipeline": "unknown",
        "ghcr_publish": "unknown",
    }

    try:
        response = requests.get(workflow_url, headers=headers, timeout=5)
        if response.status_code != 200:
            return {
                "configured": True,
                "repository": repo,
                "workflow": "devsecops.yml",
                "latest_run": None,
                "jobs": default_jobs,
                "message": f"GitHub API returned HTTP {response.status_code}: {response.json().get('message', 'Error')}",
            }

        runs_data = response.json()
        total_count = runs_data.get("total_count", 0)
        runs = runs_data.get("workflow_runs", [])

        if total_count == 0 or not runs:
            return {
                "configured": True,
                "repository": repo,
                "workflow": "devsecops.yml",
                "latest_run": None,
                "jobs": {k: "not_run" for k in default_jobs},
                "message": "Workflow found but no runs have been executed yet.",
            }

        latest_run = runs[0]
        run_id = latest_run.get("id")
        run_status = latest_run.get("status")
        run_conclusion = latest_run.get("conclusion")
        pipeline_status = map_conclusion(run_conclusion, run_status)

        # Fetch individual job details
        jobs_url = f"{base_url}/actions/runs/{run_id}/jobs"
        jobs_response = requests.get(jobs_url, headers=headers, timeout=5)

        job_statuses = default_jobs.copy()
        job_statuses["pipeline"] = pipeline_status

        if jobs_response.status_code == 200:
            jobs_list = jobs_response.json().get("jobs", [])
            for job in jobs_list:
                job_name = job.get("name", "").lower()
                j_conc = job.get("conclusion")
                j_stat = job.get("status")
                mapped = map_conclusion(j_conc, j_stat)

                if "quality-and-secrets" in job_name or "quality" in job_name:
                    job_statuses["unit_tests"] = mapped
                    job_statuses["checkov"] = mapped
                    job_statuses["gitleaks"] = mapped
                elif "docker-build-and-scan" in job_name or "docker" in job_name:
                    job_statuses["docker_build"] = mapped
                    job_statuses["trivy"] = mapped
                elif "publish-ghcr" in job_name or "publish" in job_name:
                    job_statuses["ghcr_publish"] = mapped

        return {
            "configured": True,
            "repository": repo,
            "workflow": "devsecops.yml",
            "latest_run": {
                "id": run_id,
                "html_url": latest_run.get("html_url"),
                "event": latest_run.get("event"),
                "status": run_status,
                "conclusion": run_conclusion,
                "created_at": latest_run.get("created_at"),
                "head_branch": latest_run.get("head_branch"),
                "head_sha": latest_run.get("head_sha", "")[:7],
            },
            "jobs": job_statuses,
            "message": "Pipeline status retrieved successfully from GitHub.",
        }

    except requests.exceptions.Timeout:
        return {
            "configured": True,
            "repository": repo,
            "workflow": "devsecops.yml",
            "latest_run": None,
            "jobs": default_jobs,
            "message": "GitHub API request timed out after 5.0 seconds.",
        }
    except Exception as exc:
        return {
            "configured": True,
            "repository": repo,
            "workflow": "devsecops.yml",
            "latest_run": None,
            "jobs": default_jobs,
            "message": f"Failed to fetch GitHub pipeline status: {str(exc)}",
        }


def create_app(
    model_path: Optional[str] = None, test_config: Optional[Dict[str, Any]] = None
) -> Flask:
    """Application factory for Flask app instance isolation."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    effective_model_path = model_path or os.environ.get(
        "MODEL_PATH", DEFAULT_MODEL_PATH
    )
    pipeline_cache = PipelineStatusCache(ttl_seconds=60)

    # Load machine learning model once at startup
    loaded_model = None
    if os.path.exists(effective_model_path):
        try:
            loaded_model = joblib.load(effective_model_path)
            app.logger.info(
                "Successfully loaded ML model from %s", effective_model_path
            )
        except Exception as exc:
            app.logger.error("Error loading ML model: %s", exc)
    else:
        app.logger.warning(
            "Model file not found at %s. /predict will return 503.",
            effective_model_path,
        )

    app.extensions["ml_model"] = loaded_model
    app.extensions["pipeline_cache"] = pipeline_cache

    # ---------------------------
    # Global Error Handlers (Consistent JSON shape)
    # ---------------------------
    @app.errorhandler(400)
    def handle_bad_request(err):
        description = getattr(err, "description", "Bad request syntax or invalid input")
        return jsonify({"error": description, "code": 400}), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "Resource not found", "code": 404}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        return (
            jsonify({"error": "HTTP method not allowed for this route", "code": 405}),
            405,
        )

    @app.errorhandler(415)
    def handle_unsupported_media_type(err):
        return (
            jsonify(
                {
                    "error": "Unsupported Media Type. Content-Type must be application/json",
                    "code": 415,
                }
            ),
            415,
        )

    @app.errorhandler(500)
    def handle_internal_server_error(err):
        return jsonify({"error": "Internal server error occurred", "code": 500}), 500

    # ---------------------------
    # Routes
    # ---------------------------
    @app.route("/", methods=["GET"])
    def dashboard():
        """Renders the frontend dashboard."""
        return render_template("index.html")

    @app.route("/api", methods=["GET"])
    def project_info():
        """Returns API metadata, architecture, and class descriptions."""
        return (
            jsonify(
                {
                    "name": "SecureDeploy ML",
                    "version": "1.0.0",
                    "lab_experiment": "Cloud Computing Lab DJS23ALMD701",
                    "model_type": "TF-IDF Vectorizer + Multinomial Logistic Regression",
                    "classes": ["negative", "neutral", "positive"],
                    "endpoints": {
                        "dashboard": "/",
                        "info": "/api",
                        "health": "/health",
                        "predict": "/predict",
                        "pipeline_status": "/api/pipeline-status",
                    },
                    "disclaimer": "Demonstration dataset only. Model is designed for educational learning, not financial trading.",
                }
            ),
            200,
        )

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint confirming container status and model loading."""
        model = app.extensions.get("ml_model")
        is_loaded = model is not None
        status_code = 200 if is_loaded else 503
        return (
            jsonify(
                {
                    "status": "ok" if is_loaded else "degraded",
                    "model_loaded": is_loaded,
                    "service": "securedeploy-ml",
                }
            ),
            status_code,
        )

    @app.route("/predict", methods=["POST"])
    def predict():
        """
        Validates headline input and returns predicted sentiment and confidence.
        Expects JSON: {"text": "..."}
        """
        model = app.extensions.get("ml_model")
        if model is None:
            return (
                jsonify(
                    {"error": "Model not loaded. Service unavailable.", "code": 503}
                ),
                503,
            )

        if not request.is_json:
            return (
                jsonify(
                    {
                        "error": "Unsupported Media Type. Content-Type must be application/json",
                        "code": 415,
                    }
                ),
                415,
            )

        try:
            payload = request.get_json(silent=False)
        except Exception:
            return jsonify({"error": "Malformed JSON payload", "code": 400}), 400

        if payload is None or not isinstance(payload, dict):
            return (
                jsonify(
                    {
                        "error": "Malformed JSON payload: JSON body must be an object",
                        "code": 400,
                    }
                ),
                400,
            )

        if "text" not in payload:
            return jsonify({"error": "Field 'text' is required", "code": 400}), 400

        raw_text = payload.get("text")
        if not isinstance(raw_text, str):
            return jsonify({"error": "Field 'text' must be a string", "code": 400}), 400

        trimmed_text = raw_text.strip()
        if len(trimmed_text) == 0:
            return (
                jsonify(
                    {"error": "Field 'text' cannot be empty or whitespace", "code": 400}
                ),
                400,
            )

        if len(trimmed_text) < 3:
            return (
                jsonify(
                    {
                        "error": "Field 'text' must be at least 3 characters long",
                        "code": 400,
                    }
                ),
                400,
            )

        if len(trimmed_text) > 500:
            return (
                jsonify(
                    {
                        "error": "Field 'text' must not exceed 500 characters",
                        "code": 400,
                    }
                ),
                400,
            )

        # Run inference
        probs = model.predict_proba([trimmed_text])[0]
        classes = model.classes_
        prob_dict = {str(c): float(round(p, 4)) for c, p in zip(classes, probs)}
        predicted_label = str(model.predict([trimmed_text])[0])
        confidence = float(round(max(probs), 4))

        return (
            jsonify(
                {
                    "label": predicted_label,
                    "confidence": confidence,
                    "probabilities": prob_dict,
                }
            ),
            200,
        )

    @app.route("/api/pipeline-status", methods=["GET"])
    def pipeline_status():
        """
        Returns latest GitHub Actions workflow summary for devsecops.yml.
        Uses GITHUB_REPOSITORY and optional GITHUB_TOKEN environment variables.
        Cached in-memory for 60 seconds.
        """
        cache: PipelineStatusCache = app.extensions["pipeline_cache"]
        cached = cache.get()
        if cached:
            result = cached.copy()
            result["cached"] = True
            return jsonify(result), 200

        repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
        token = os.environ.get("GITHUB_TOKEN", "").strip() or None

        if not repo:
            unconfigured_result = {
                "configured": False,
                "repository": None,
                "workflow": "devsecops.yml",
                "latest_run": None,
                "jobs": {
                    "unit_tests": "unknown",
                    "docker_build": "unknown",
                    "trivy": "unknown",
                    "checkov": "unknown",
                    "gitleaks": "unknown",
                    "pipeline": "unknown",
                    "ghcr_publish": "unknown",
                },
                "cached": False,
                "message": "GITHUB_REPOSITORY environment variable is not configured. Running in local standalone mode.",
            }
            cache.set(unconfigured_result)
            return jsonify(unconfigured_result), 200

        live_result = fetch_github_pipeline_status(repo, token)
        live_result["cached"] = False
        cache.set(live_result)
        return jsonify(live_result), 200

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app_instance = create_app()
    print(f"[*] Starting SecureDeploy ML server on http://0.0.0.0:{port}")
    app_instance.run(host="0.0.0.0", port=port, debug=False)
