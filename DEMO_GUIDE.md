# SecureDeploy ML &mdash; Live Demonstration & Presentation Guide
## 6-to-8 Minute Lab Viva Script & Commands
### Cloud Computing Lab (DJS23ALMD701)

---

## Preparation Checklist Before the Presentation
- [ ] Open PowerShell in the project directory: `c:\Users\Varshil Jain\Desktop\CCL`
- [ ] Activate Python virtual environment: `.\venv\Scripts\Activate.ps1`
- [ ] Start Docker Desktop (if demonstrating local container execution)
- [ ] Have your browser open to [http://localhost:5000](http://localhost:5000)

---

## Timed 6-8 Minute Presentation Script

### Minute 0:00 &ndash; 1:00: Introduction & Overview
**What to Say:**
> *"Good morning, sir/madam. Today I will demonstrate **SecureDeploy ML**, our DevSecOps mini-project for Cloud Computing Lab (DJS23ALMD701).
> The project packages a Financial News Sentiment Classifier with production-grade containerization in Experiment 4, automated security scanning with Trivy, Checkov, and Gitleaks in Experiment 8, and an automated GitHub Actions CI/CD pipeline publishing to GHCR in Experiment 13."*

**Action:**
Show the project folder structure in VS Code or Terminal:
```powershell
Get-ChildItem -Name
```

---

### Minute 1:00 &ndash; 2:30: Model Training & Local Application Demo
**What to Say:**
> *"First, let's look at the ML core. We trained a deterministic NLP pipeline using TF-IDF vectorization and Multinomial Logistic Regression on 180 balanced financial headlines. Let's run the training script."*

**Command to Run:**
```powershell
python train.py
```
**Point Out to Evaluator:**
- The dataset loaded 180 headlines (60 positive, 60 negative, 60 neutral).
- The held-out split produced an honest test accuracy of **61.11%** with a macro F1 of **0.5935**.
- `model.joblib` was serialized locally.

**What to Say Next:**
> *"Now let's launch the local Flask application and view the responsive dashboard."*

**Command to Run:**
```powershell
python app.py
```
*Open browser to `http://localhost:5000`:*
1. Point to the top-right badge: **API: Healthy (Model Loaded)**.
2. Click the quick example chip: **Profit Surge (+35%)**.
3. Click **Analyze Sentiment**. Point out the **POSITIVE** badge, **confidence score**, and the per-class probability bars.
4. Click the example chip: **Losses Widen (-18%)** and analyze &rarr; point to **NEGATIVE**.
5. Point out the **Recent Analyses** section maintaining the last 5 inferences in session memory without localStorage.
6. Click the **DevSecOps Status** navigation tab &rarr; point out the status cards and the banner explaining local standalone mode.

---

### Minute 2:30 &ndash; 3:30: Automated Pytest Suite & Code Quality
**What to Say:**
> *"Next, let's examine code quality. We enforce strict PEP 8 formatting with Black, pre-compilation checks, and 20 automated Pytest test cases covering boundary validation, error handling, mathematical integrity, and instance isolation."*

**Command to Run (in a second terminal):**
```powershell
# Verify syntax pre-compilation
python -m compileall -q app.py train.py tests

# Verify dependency graph
python -m pip check

# Verify code formatting gate
black --check .

# Run 20 automated tests
pytest -v
```
**Point Out to Evaluator:**
- All 20 tests pass in ~1.5 seconds with 100% pass rate.
- Highlight `test_predict_unsupported_media_type` (HTTP 415) and `test_prediction_confidence_and_probability_sum` (probabilities sum to 1.0).

---

### Minute 3:30 &ndash; 5:00: Docker Multi-Stage & Non-Root Security (Exp 4)
**What to Say:**
> *"In Experiment 4, we engineered a production-ready multi-stage Dockerfile. Stage 1 builds the venv and bakes the model artifact, while Stage 2 is a clean `python:3.12-slim` image containing only runtime dependencies.
> Crucially, it runs as an unprivileged user (UID 10001) and includes a zero-dependency Python healthcheck."*

**Commands to Run:**
```powershell
# 1. Build production multi-stage image
docker build --pull -t securedeploy:local .

# 2. Run container mapping port 5000
docker run -d --name securedeploy-demo -p 5000:5000 securedeploy:local

# 3. Check health status
docker inspect --format='{{.State.Health.Status}}' securedeploy-demo

# 4. Prove container runs as unprivileged non-root user
docker exec securedeploy-demo id

# 5. Clean up
docker stop securedeploy-demo
docker rm securedeploy-demo
```
**Point Out to Evaluator:**
- `docker exec ... id` prints `uid=10001(appuser) gid=10001(appgroup)`. This proves the container cannot gain host root privileges.

---

### Minute 5:00 &ndash; 6:30: Security Scanners & Safe Demonstrations (Exp 8)
**What to Say:**
> *"In Experiment 8, we automate security scanning across secrets, IaC, and container vulnerabilities using Gitleaks, Checkov, and Trivy.*
> *We have an automated script `scripts/security_scan.ps1` that coordinates these scans and exports reports to `reports/`."*

**Command to Run:**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\security_scan.ps1
```

#### Safe Demo 1: Gitleaks Secret Detection (Outside the Repo)
**What to Say:**
> *"To safely prove Gitleaks works without leaking secrets into our project, let's create a temporary git repository in a temp directory, simulate a committed credential, and observe Gitleaks catching it."*

**Command to Run:**
```powershell
# Create temporary folder outside repository
$TempDir = Join-Path $env:TEMP "gitleaks-demo-$(Get-Random)"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
Set-Location $TempDir

# Initialize git and simulate committing a dummy AWS token pattern
git init
"AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" | Out-File -Encoding utf8 credentials.env
git add credentials.env
git commit -m "test: simulate secret commit"

# Run Gitleaks detect
gitleaks detect --source . --verbose

# Clean up temp folder immediately
Set-Location "c:\Users\Varshil Jain\Desktop\CCL"
Remove-Item -Recurse -Force $TempDir
```
**Point Out to Evaluator:**
- Gitleaks immediately triggers with exit code 1, identifying the `aws-access-token` pattern and file path.
- The repository was completely untouched.

#### Safe Demo 2: Checkov Finding Flaws in `demo/Dockerfile.insecure`
**What to Say:**
> *"To demonstrate Checkov and Trivy config scanning, we created `demo/Dockerfile.insecure` with deliberate anti-patterns (runs as root, unpinned python:latest, missing healthcheck, remote ADD). Let's scan it."*

**Command to Run:**
```powershell
# Scan insecure Dockerfile with Checkov
checkov -f demo/Dockerfile.insecure --framework dockerfile
```
**Point Out to Evaluator:**
- Checkov flags violations: `CKV_DOCKER_2` (missing HEALTHCHECK), `CKV_DOCKER_3` (missing USER), `CKV_DOCKER_7` (unpinned latest tag), `CKV_DOCKER_11` (ADD used instead of COPY).
- Compare this with our production `Dockerfile` which passes all checks!

---

### Minute 6:30 &ndash; 7:30: CI/CD Pipeline & GHCR Publishing (Exp 13)
**What to Say:**
> *"Finally, in Experiment 13, our 3-job GitHub Actions workflow (`devsecops.yml`) ties everything together:*
> 1. *Job 1: Tests, lints, and scans secrets with Gitleaks and IaC with Checkov.*
> 2. *Job 2: Builds the image with Buildx, scans with Trivy for fixable HIGH/CRITICAL CVEs, performs a live smoke test, and exports the image artifact.*
> 3. *Job 3: On merge to main, downloads the verified image artifact without rebuilding, logs into GHCR, tags it with main, commit SHA, and latest, and publishes it to ghcr.io.*
> *This guarantees that the exact bytes scanned and tested are what enters production."*

**Action:**
Show `.github/workflows/devsecops.yml` in VS Code or GitHub web UI, pointing out:
- Pinned action versions with full commit SHAs.
- Artifact upload and download steps.
- Conditional GHCR publish restricted to `push` on `refs/heads/main`.

---

## Backup Plan & Troubleshooting

| Scenario | Immediate Fallback Action | What to Explain to Evaluator |
| :--- | :--- | :--- |
| **Docker Desktop not running or slow** | Use `python app.py` for live demo and show the Dockerfile code and pre-saved command logs. | Explain: *"The application code is fully runnable locally via Python. The multi-stage Dockerfile is validated for CI/CD runners where Docker is provisioned by GitHub."* |
| **Scanner binary missing on host machine** | Run the safe demo commands or explain `scripts/security_scan.ps1`. | Explain: *"In production DevSecOps, scanners run in the standardized Ubuntu CI runner environment in `.github/workflows/devsecops.yml`."* |
| **Port 5000 is occupied** | Run with `$env:PORT="5001"; python app.py` | Explain: *"Our Flask app factory reads dynamic port environment variables to adapt to port availability gracefully."* |
| **GitHub Actions runner queued/delayed** | Show the local Pytest XML and local scan logs in `reports/`. | Explain: *"The pipeline jobs are identical in logic to our local test and scan scripts."* |

---

## Lab Viva Screenshot Checklist

1. [ ] **Model Training:** `python train.py` showing `61.11%` test accuracy.
2. [ ] **Pytest Verification:** `pytest -v` showing all 20 tests passed.
3. [ ] **Dashboard Classifier:** Browser at `http://localhost:5000` showing positive/negative predictions.
4. [ ] **Dashboard DevSecOps:** Browser DevSecOps tab with status cards.
5. [ ] **Docker Execution:** `docker exec securedeploy-demo id` verifying `UID 10001`.
6. [ ] **Local Scan Script:** `powershell .\scripts\security_scan.ps1` summary table.
7. [ ] **GitHub Actions CI/CD:** GitHub web page showing green 3-job pipeline.
8. [ ] **GHCR Package:** GitHub profile Packages tab showing published container image.
