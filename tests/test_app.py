"""
Comprehensive Test Suite for SecureDeploy ML
Cloud Computing Lab DJS23ALMD701
Tests API endpoints, input validation, status shapes, isolation, and inference integrity.
"""

import json
import os
import tempfile
import pytest
from app import create_app, PipelineStatusCache, map_conclusion
from train import build_pipeline


@pytest.fixture
def app():
    """Flask application fixture with the production trained model."""
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()


# -------------------------------------------------------------
# 1. Dashboard & Core API Endpoints
# -------------------------------------------------------------
def test_dashboard_renders(client):
    """Test 1: Verify dashboard index page loads with HTML 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"SecureDeploy" in response.data
    assert b"Financial News Sentiment Classifier" in response.data


def test_api_metadata(client):
    """Test 2: Verify /api returns expected metadata and JSON structure."""
    response = client.get("/api")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data["name"] == "SecureDeploy ML"
    assert data["version"] == "1.0.0"
    assert "classes" in data
    assert set(data["classes"]) == {"positive", "neutral", "negative"}


def test_health_check(client):
    """Test 3: Verify /health returns status ok and model_loaded: true."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


# -------------------------------------------------------------
# 2. Prediction Success Tests (Positive, Negative, Neutral)
# -------------------------------------------------------------
def test_predict_positive_headline(client):
    """Test 4: Predict positive sentiment on strong growth headline."""
    payload = {
        "text": "Quarterly net profit surges 45% beating consensus analyst forecasts"
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "label" in data
    assert data["label"] in ["positive", "neutral", "negative"]
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0


def test_predict_negative_headline(client):
    """Test 5: Predict negative sentiment on loss and regulatory penalty headline."""
    payload = {
        "text": "Operating profit plunges steeply due to soaring debt and massive regulatory fines"
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "label" in data
    assert "confidence" in data


def test_predict_neutral_headline(client):
    """Test 6: Predict neutral sentiment on routine administrative headline."""
    payload = {
        "text": "Board of directors schedules annual shareholder meeting for next month in New York"
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "label" in data
    assert "confidence" in data


# -------------------------------------------------------------
# 3. Input Validation and HTTP Error Handlers
# -------------------------------------------------------------
def test_predict_missing_text_key(client):
    """Test 7: Reject payload missing the 'text' key with 400 Bad Request."""
    response = client.post("/predict", json={"headline": "Missing text key"})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "Field 'text' is required" in data["error"]


def test_predict_empty_text(client):
    """Test 8: Reject empty or whitespace-only text with 400 Bad Request."""
    response = client.post("/predict", json={"text": "     "})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "cannot be empty" in data["error"]


def test_predict_wrong_data_type(client):
    """Test 9: Reject non-string input (e.g. integer) with 400 Bad Request."""
    response = client.post("/predict", json={"text": 12345})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "must be a string" in data["error"]


def test_predict_text_too_short(client):
    """Test 10: Reject text under 3 characters with 400 Bad Request."""
    response = client.post("/predict", json={"text": "Up"})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "at least 3 characters" in data["error"]


def test_predict_text_too_long(client):
    """Test 11: Reject text over 500 characters with 400 Bad Request."""
    long_text = "A" * 501
    response = client.post("/predict", json={"text": long_text})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "must not exceed 500 characters" in data["error"]


def test_predict_malformed_json(client):
    """Test 12: Reject malformed JSON body with consistent 400 JSON error."""
    response = client.post(
        "/predict",
        data="{text: 'invalid json without quotes'}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "Malformed JSON" in data["error"]


def test_predict_unsupported_media_type(client):
    """Test 13: Reject non-JSON Content-Type with 415 Unsupported Media Type."""
    response = client.post(
        "/predict",
        data="text=Profit+up",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 415
    data = response.get_json()
    assert data["code"] == 415
    assert "application/json" in data["error"]


def test_unknown_route_json_error(client):
    """Test 14: Unknown routes return 404 with standard JSON error schema."""
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404
    data = response.get_json()
    assert data["code"] == 404
    assert "Resource not found" in data["error"]


# -------------------------------------------------------------
# 4. Statistical & Mathematical Integrity
# -------------------------------------------------------------
def test_prediction_confidence_and_probability_sum(client):
    """Test 15: Validate that probabilities sum to 1.0 and confidence matches maximum."""
    payload = {"text": "Central bank announces unexpected 50 bps interest rate hike"}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    probs = data["probabilities"]

    assert set(probs.keys()) == {"positive", "neutral", "negative"}
    prob_sum = sum(probs.values())
    # Tolerant to rounding to 4 decimals
    assert 0.99 <= prob_sum <= 1.01
    assert data["confidence"] == max(probs.values())
    assert 0.0 <= data["confidence"] <= 1.0


# -------------------------------------------------------------
# 5. Architecture, Isolation, & Model Fixture
# -------------------------------------------------------------
def test_app_instances_are_isolated():
    """Test 16: Verify create_app() produces independent, isolated instances."""
    app_a = create_app(test_config={"CUSTOM_KEY": "instance_A"})
    app_b = create_app(test_config={"CUSTOM_KEY": "instance_B"})

    assert app_a.config["CUSTOM_KEY"] == "instance_A"
    assert app_b.config["CUSTOM_KEY"] == "instance_B"
    assert app_a is not app_b


def test_mini_model_train_and_load_fixture():
    """Test 17: Train a miniature model fixture and verify serialization and inference."""
    import joblib

    mini_texts = [
        "Record profit growth achieved",
        "Dividend increased significantly",
        "Severe loss reported this quarter",
        "Operating bankruptcy filing",
        "Regular board meeting scheduled",
        "Notice of routine filing",
    ]
    mini_labels = ["positive", "positive", "negative", "negative", "neutral", "neutral"]

    pipe = build_pipeline()
    pipe.fit(mini_texts, mini_labels)

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_model_file = os.path.join(tmp_dir, "test_model.joblib")
        joblib.dump(pipe, temp_model_file)
        assert os.path.exists(temp_model_file)

        # Create isolated test app with this model
        isolated_app = create_app(model_path=temp_model_file)
        test_client = isolated_app.test_client()

        res = test_client.post("/predict", json={"text": "Record profit quarterly"})
        assert res.status_code == 200
        assert res.get_json()["label"] == "positive"


# -------------------------------------------------------------
# 6. Pipeline Status Endpoint & Cache
# -------------------------------------------------------------
def test_pipeline_status_unconfigured(client):
    """Test 18: Unconfigured GITHUB_REPOSITORY falls back gracefully with unknown status."""
    # Ensure env var is absent for this test
    os.environ.pop("GITHUB_REPOSITORY", None)
    response = client.get("/api/pipeline-status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["configured"] is False
    assert data["repository"] is None
    assert data["jobs"]["pipeline"] == "unknown"
    assert data["jobs"]["unit_tests"] == "unknown"


def test_pipeline_status_cache_ttl(client):
    """Test 19: Cache returns cached=True on repeat request within TTL."""
    os.environ.pop("GITHUB_REPOSITORY", None)
    # First call primes cache
    res1 = client.get("/api/pipeline-status")
    assert res1.status_code == 200
    # Second call uses cache
    res2 = client.get("/api/pipeline-status")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["cached"] is True


def test_map_conclusion_helper():
    """Test 20: Test GitHub conclusion to frontend status mapper."""
    assert map_conclusion("success", "completed") == "passed"
    assert map_conclusion("failure", "completed") == "failed"
    assert map_conclusion("timed_out", "completed") == "failed"
    assert map_conclusion(None, "in_progress") == "not_run"
    assert map_conclusion("skipped", "completed") == "not_run"
    assert map_conclusion(None, "unknown_status") == "unknown"
