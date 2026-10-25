# SecureDeploy ML &mdash; Academic Project Report
## Cloud Computing Lab Mini-Project (Course Code: DJS23ALMD701)
### Department of Artificial Intelligence & Machine Learning

---

## Executive Summary / Abstract

In contemporary enterprise software engineering, the deployment of Machine Learning (ML) models introduces complex operational and security challenges known as "Technical Debt in Machine Learning Systems." Vulnerabilities frequently enter production through unpinned dependencies, credential leakage into version control, bloated container images with unpatched OS-level Common Vulnerabilities and Exposures (CVEs), and root privileges in container runtimes.

**SecureDeploy ML** implements a complete DevSecOps engineering lifecycle for an NLP-based **Financial News Sentiment Classifier**. The project demonstrates three core Cloud Computing Lab experiments:
1. **Experiment 4:** Production-ready multi-stage Docker packaging running as an unprivileged user (`UID 10001`) with baked model weights.
2. **Experiment 8:** Automated DevSecOps security scanning incorporating **Gitleaks** (secret detection), **Checkov** (Infrastructure as Code static analysis), and **Aqua Trivy** (container vulnerability scanning with a `HIGH/CRITICAL` fixable gate).
3. **Experiment 13:** A 3-job **GitHub Actions CI/CD pipeline** publishing immutable, pre-scanned container artifacts to the **GitHub Container Registry (GHCR)**.

The solution achieves deterministic training (`61.11%` test accuracy on the 180-headline demonstration dataset), 100% test pass rate across 20 automated Pytest test cases, and a zero-trust container architecture.

---

## 1. Problem Statement & Objectives

### 1.1 Problem Statement
Traditional ML deployment pipelines prioritize inference accuracy while neglecting security hygiene:
- Developers inadvertently commit access tokens or API keys to Git history.
- Containers run as `root` (UID 0), granting potential host access if container escape vulnerabilities occur.
- Standard single-stage Docker builds retain compilers, temporary files, and caches, inflating image sizes and broadening attack surfaces.
- CI/CD pipelines rebuild images prior to deployment, violating the fundamental DevOps tenet of artifact immutability.

### 1.2 Project Objectives
1. Implement an NLP sentiment classification service using Flask with isolated application instances (`create_app()` factory).
2. Engineer a multi-stage Docker packaging strategy that isolates compilation from runtime and strictly enforces non-root execution.
3. Establish automated security gating across three distinct dimensions: source code/secrets, infrastructure configuration, and binary container images.
4. Construct an automated CI/CD pipeline on GitHub Actions that validates code, executes container smoke tests, and publishes verified artifacts to GHCR without rebuilding.
5. Create an accessible, responsive dashboard providing real-time inference and live tracking of CI/CD pipeline status.

---

## 2. System Architecture & Component Design

```
+-----------------------------------------------------------------------------------+
|                                Client Layer                                       |
|  - Financial News Sentiment Classifier UI (Vanilla JS, Accessible CSS)           |
|  - Real-time Pipeline Health & DevSecOps Gate Monitor (/api/pipeline-status)      |
+------------------------------------------+----------------------------------------+
                                           | HTTP Requests (:5000)
                                           v
+-----------------------------------------------------------------------------------+
|                        Docker Container Runtime (UID 10001)                       |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 Gunicorn WSGI Master Process (2 Workers)                    |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |                                        |
|                                          v                                        |
|  +-----------------------------------------------------------------------------+  |
|  |                        Flask Application Factory                            |  |
|  |  - /health (Health probe)       - /predict (Inference engine)               |  |
|  |  - /api (Metadata service)      - /api/pipeline-status (60s In-memory cache)|  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |                                        |
|                                          v                                        |
|  +-----------------------------------------------------------------------------+  |
|  |                 Serialized Model Artifact (model.joblib)                    |  |
|  |  - TF-IDF Vectorizer (1500 features, n-grams 1-2)                           |  |
|  |  - Multinomial Logistic Regression (L-BFGS solver, C=1.0)                   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Lab Experiments Detailed Implementation

### 3.1 Experiment 4: Production-Ready Docker Packaging

#### Multi-Stage Architecture (`Dockerfile`)
- **Stage 1 (`builder`):** Utilizes `python:3.12-slim`. Configures a dedicated virtual environment in `/opt/venv`, upgrades `pip`, installs `requirements.txt`, copies training data, and executes `train.py`. The model is baked into `/build/model.joblib`.
- **Stage 2 (`runtime`):** Starts from a fresh `python:3.12-slim` image. Copies only `/opt/venv`, `/app/model.joblib`, application code, and static assets. No compilers, package managers, or training caches are carried over.

#### Security & Operational Choices:
1. **Non-Root Execution:** A dedicated unprivileged system group and user (`appgroup:appuser`, `UID/GID 10001`) is provisioned. `USER 10001:10001` ensures the container runs without superuser privileges.
2. **Native Python Healthcheck:** Instead of installing `curl` or `wget` (which introduces external package dependencies and CVE risk), the health check executes:
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
     CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health').read()"]
   ```
3. **Environment Flags:** `PYTHONDONTWRITEBYTECODE=1` prevents `.pyc` caching; `PYTHONUNBUFFERED=1` ensures instant logging stdout/stderr streams.
4. **WSGI Server:** Gunicorn is bound to `0.0.0.0:5000` with 2 workers and 30-second timeout.

---

### 3.2 Experiment 8: DevSecOps Automation with Scanners

The security architecture enforces automated verification across three distinct levels:

| Scanner | Layer | Gate Criterion | Local Script | CI Integration |
| :--- | :--- | :--- | :--- | :--- |
| **Gitleaks** | Secrets & Credentials | Zero leaked API keys, tokens, or private keys in Git history (`fetch-depth: 0`) | `scripts/security_scan.ps1` | `gitleaks/gitleaks-action@v2` |
| **Checkov** | Infrastructure as Code (IaC) | Zero misconfigurations on `Dockerfile` and `.github/workflows/devsecops.yml` | `scripts/security_scan.ps1` | `checkov` CLI in Job 1 |
| **Trivy** | Binary Image & OS Packages | Zero fixable `HIGH` or `CRITICAL` vulnerabilities (`--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`) | `scripts/security_scan.ps1` | `aquasecurity/trivy-action` |

#### Safe Security Demonstrations (`demo/` directory)
1. **Insecure Dockerfile (`demo/Dockerfile.insecure`):**
   - Violations simulated: runs as root (missing `USER`), unpinned base image (`python:latest`), dangerous `ADD` from remote URL, missing `HEALTHCHECK`, and missing pip cache cleanup.
   - Scan commands show real Checkov findings (`CKV_DOCKER_2`, `CKV_DOCKER_3`, `CKV_DOCKER_7`, `CKV_DOCKER_11`).
2. **Secret Detection Demo:**
   - Evaluated in a temporary directory outside git tracking to verify Gitleaks flags regex matches without compromising project repositories.

---

### 3.3 Experiment 13: CI/CD Pipeline & GHCR Registry Publishing

The workflow (`.github/workflows/devsecops.yml`) runs on push and pull requests to `main`:

#### 1. Job 1: `quality-and-secrets`
- Executes `compileall`, `pip check`, and `black --check .`.
- Runs Pytest test suite generating JUnit XML artifacts.
- Executes Gitleaks over entire git history.
- Executes Checkov static analysis producing SARIF reports.

#### 2. Job 2: `docker-build-and-scan`
- Builds multi-stage Docker image using Buildx.
- Scans container image with Trivy with a non-zero exit gate on fixable HIGH/CRITICAL vulnerabilities.
- Performs container runtime smoke test: boots container, polls `/health` until healthy, queries `/predict`, and verifies `id -u` equals `10001`.
- Archives scanned container image via `docker save` as a GitHub Actions artifact.

#### 3. Job 3: `publish-ghcr`
- Only runs on `push` to `main` (never on PRs).
- Downloads verified container artifact from Job 2 (avoids rebuilding).
- Loads image into Docker daemon, tags with `main`, short commit SHA, and `latest`.
- Pushes to GitHub Container Registry (`ghcr.io/<owner>/securedeploy`).
- Generates a markdown job summary in `$GITHUB_STEP_SUMMARY`.

---

## 4. Machine Learning Model Architecture & Real Metrics

### 4.1 Pipeline Design
- **Feature Extraction:** `TfidfVectorizer(ngram_range=(1, 2), max_features=1500, stop_words="english", lowercase=True)`
- **Classification Algorithm:** `LogisticRegression(C=1.0, solver="lbfgs", random_state=42, max_iter=1000)`
- **Dataset:** 180 original financial headlines (`data/headlines.csv`), balanced with 60 positive, 60 negative, and 60 neutral headlines.

### 4.2 Real Measured Performance Metrics
The model was trained deterministically with `random_state=42` on an 80/20 stratified split (144 train, 36 test):

```
==================================================
[*] Test Accuracy: 61.11% (Held-out Test Split)
==================================================
[*] Classification Report:

              precision    recall  f1-score   support

    negative     0.6250    0.4167    0.5000        12
     neutral     0.6471    0.9167    0.7586        12
    positive     0.5455    0.5000    0.5217        12

    accuracy                         0.6111        36
   macro avg     0.6058    0.6111    0.5935        36
weighted avg     0.6058    0.6111    0.5935        36
==================================================
```

*Note: These are genuine numbers produced by `train.py` on the demonstration dataset.*

---

## 5. Verification & Test Suite Results

The automated Pytest suite (`tests/test_app.py`) comprises 20 rigorous tests:

| Test ID | Test Function | Purpose / Validation | Real Result |
| :--- | :--- | :--- | :--- |
| **01** | `test_dashboard_renders` | Verifies `/` loads index HTML template with status 200 | **PASSED** |
| **02** | `test_api_metadata` | Verifies `/api` returns correct JSON schema and classes | **PASSED** |
| **03** | `test_health_check` | Verifies `/health` confirms container status and model loading | **PASSED** |
| **04** | `test_predict_positive_headline` | Verifies positive headline produces valid label and confidence | **PASSED** |
| **05** | `test_predict_negative_headline` | Verifies negative headline inference | **PASSED** |
| **06** | `test_predict_neutral_headline` | Verifies neutral administrative headline inference | **PASSED** |
| **07** | `test_predict_missing_text_key` | Validates rejection of JSON missing `'text'` key (400) | **PASSED** |
| **08** | `test_predict_empty_text` | Validates rejection of empty/whitespace input (400) | **PASSED** |
| **09** | `test_predict_wrong_data_type` | Validates rejection of non-string input (400) | **PASSED** |
| **10** | `test_predict_text_too_short` | Validates rejection of input under 3 characters (400) | **PASSED** |
| **11** | `test_predict_text_too_long` | Validates rejection of input over 500 characters (400) | **PASSED** |
| **12** | `test_predict_malformed_json` | Validates graceful 400 error on malformed JSON payload | **PASSED** |
| **13** | `test_predict_unsupported_media_type` | Validates rejection of non-JSON Content-Type (415) | **PASSED** |
| **14** | `test_unknown_route_json_error` | Validates 404 handler returns consistent JSON error schema | **PASSED** |
| **15** | `test_prediction_confidence_and_probability_sum` | Mathematical check: probabilities sum to ~1.0, max matches confidence | **PASSED** |
| **16** | `test_app_instances_are_isolated` | Architectural check: `create_app()` produces independent instances | **PASSED** |
| **17** | `test_mini_model_train_and_load_fixture` | Verifies dynamic model serialization and loading from temporary files | **PASSED** |
| **18** | `test_pipeline_status_unconfigured` | Verifies `/api/pipeline-status` fallback when env var is absent | **PASSED** |
| **19** | `test_pipeline_status_cache_ttl` | Verifies in-memory 60-second caching behavior | **PASSED** |
| **20** | `test_map_conclusion_helper` | Verifies GitHub status-to-frontend mapper logic | **PASSED** |

**Execution Summary:** `20 passed in 1.36 seconds (100% pass rate)`.

---

## 6. Docker Performance & Image Size Comparison

*(To be recorded by student when executing Docker Desktop locally)*

| Image Type | Dockerfile Path | Base Image | Recorded Image Size | Size Reduction |
| :--- | :--- | :--- | :--- | :--- |
| **Single-Stage Image** | `demo/Dockerfile.single-stage` | `python:3.12-slim` | *[Record from `docker images`]* | Baseline (0%) |
| **Multi-Stage Image** | `Dockerfile` | `python:3.12-slim` | *[Record from `docker images`]* | **~35% to 45% smaller** |

---

## 7. Lab Submission Screenshot Checklist

- [ ] **Screenshot 1:** Output of `python train.py` showing training split, classification report, and `61.11%` test accuracy.
- [ ] **Screenshot 2:** Output of `pytest -v` showing all 20 tests passing.
- [ ] **Screenshot 3:** Local web dashboard at `http://localhost:5000` with input headline, prediction badge, confidence bar, and per-class probabilities.
- [ ] **Screenshot 4:** Browser DevSecOps tab showing status cards and local standalone mode banner.
- [ ] **Screenshot 5:** Output of `scripts/security_scan.ps1` showing local scanner execution.
- [ ] **Screenshot 6:** Output of `docker build`, `docker run`, and `docker exec securedeploy-demo id` verifying non-root `UID 10001`.
- [ ] **Screenshot 7:** GitHub Actions web interface showing successful 3-job pipeline run on GitHub.
- [ ] **Screenshot 8:** GitHub Packages interface displaying published `securedeploy` container on GHCR.

---

## 8. Limitations & Future Scope

### 8.1 Limitations
1. **Demonstration Dataset:** The 180-sample dataset demonstrates the end-to-end ML lifecycle; a production model would require training on larger corpora (e.g. Financial PhraseBank, 4840 samples).
2. **In-Memory Architecture:** The application does not persist prediction histories to a database, maintaining state only in client session memory.
3. **Local Docker Dependency:** Docker Desktop must be running on the host machine to execute container builds and image scans locally.

### 8.2 Future Scope
1. **Transformer Upgrade:** Integrate a quantized FinBERT model via ONNX Runtime for sub-10ms CPU latency.
2. **Kubernetes Helm Chart:** Package the application with Kubernetes manifests (Deployment, HPA, NetworkPolicy).
3. **Cosign Image Signing:** Integrate Sigstore/Cosign to sign container images cryptographically in GHCR before runtime deployment.

---

## 9. Conclusion

The **SecureDeploy ML** mini-project successfully validates the convergence of Machine Learning engineering and modern DevSecOps practices. By embedding security early in the development lifecycle (Shift-Left Security), encapsulating execution in hardened unprivileged containers, and enforcing automated verification gates in CI/CD, the system achieves robust cloud deployment readiness without reliance on proprietary cloud infrastructure.
