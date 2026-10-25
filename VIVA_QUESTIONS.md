# SecureDeploy ML &mdash; Comprehensive Viva Examination Guide
## Cloud Computing Lab (DJS23ALMD701)
### 35+ Viva Q&A &bull; 1-Minute Elevator Pitch &bull; 5 Tricky Evaluator Questions

---

## Part 1: The One-Minute Project Summary (Elevator Pitch)

> *"Good morning, examiners. My mini-project is **SecureDeploy ML**, which demonstrates end-to-end DevSecOps engineering for an NLP financial news sentiment classifier.*
>
> *We implemented three lab experiments:*
> 1. *In **Experiment 4**, we engineered a production-ready, multi-stage Docker container where the ML model is baked in during the build stage, running as an unprivileged non-root user (UID 10001) with internal Python healthchecking.*
> 2. *In **Experiment 8**, we established automated DevSecOps security gates using **Gitleaks** to detect leaked credentials, **Checkov** to inspect Infrastructure-as-Code files, and **Aqua Trivy** to block images containing fixable High or Critical vulnerabilities.*
> 3. *In **Experiment 13**, we constructed a 3-job **GitHub Actions CI/CD pipeline** that tests, scans, smoke-tests, and publishes the verified container artifact directly to **GitHub Container Registry (GHCR)** without rebuilding the image.*
>
> *The system achieves 100% test pass across 20 Pytest test cases, enforces strict REST input validation, and provides an accessible dashboard tracking both live inferences and real-time GitHub Actions workflow status."*

---

## Part 2: 35 Core Viva Questions & Answers

### Group A: Cloud, DevOps & DevSecOps Fundamentals

#### Q1: What is DevSecOps and how does it differ from traditional DevOps?
**Answer:** Traditional DevOps focuses on speed and automation across development and operations (CI/CD). DevSecOps "shifts security left," embedding automated security checks (secret scanning, static analysis, container vulnerability scanning) at every phase of the pipeline rather than treating security as an afterthought or manual audit at the end.

#### Q2: What is the principle of "Shift-Left"?
**Answer:** Shift-Left means moving testing and security verification earlier in the Software Development Life Cycle (SDLC). Finding bugs and vulnerabilities during local commits or CI quality gates is exponentially cheaper and faster to fix than discovering them in production.

#### Q3: What is "Technical Debt in Machine Learning Systems"?
**Answer:** Unlike conventional code, ML systems carry hidden debt through glue code, pipeline complexity, data dependencies, and unpinned ML library versions. SecureDeploy ML mitigates this by baking models into immutable containers, pinning exact dependencies, and running deterministic training pipelines with fixed seeds.

#### Q4: Why is artifact immutability a foundational DevOps principle?
**Answer:** An artifact (like a Docker image) must be built once, rigorously scanned and tested, and then promoted directly across environments (dev &rarr; staging &rarr; prod / GHCR). Rebuilding the image in later pipeline stages introduces non-determinism, differing upstream packages, and invalidates previously executed scans.

---

### Group B: REST API, Flask Architecture & Machine Learning

#### Q5: Why did you use the Application Factory pattern (`create_app()`) in Flask?
**Answer:** The application factory pattern creates isolated Flask app instances dynamically. This allows our test suite in `tests/test_app.py` to instantiate fresh app instances with custom test configurations (e.g. `TESTING=True` or alternate model paths) without state pollution or global variable leakage between tests.

#### Q6: Explain the REST API design in your project.
**Answer:** We follow standard REST conventions:
- `GET /` serves the dashboard HTML.
- `GET /api` provides machine-readable API metadata.
- `GET /health` provides a health probe returning 200/503.
- `POST /predict` accepts a JSON payload `{"text": "..."}` and returns predicted sentiment, confidence, and class probabilities.
- `GET /api/pipeline-status` returns GitHub Actions pipeline health with a 60-second in-memory cache.
- All errors return consistent JSON: `{"error": "<msg>", "code": <status>}`.

#### Q7: Why do you reject requests with HTTP 415 and 400?
**Answer:** HTTP 415 (Unsupported Media Type) rejects non-JSON payloads (e.g. `text/plain` or form-data) to ensure content negotiation integrity. HTTP 400 (Bad Request) rejects malformed JSON, missing `'text'` keys, non-string types, or text outside the 3 to 500 character limits.

#### Q8: How does TF-IDF feature extraction work?
**Answer:** Term Frequency-Inverse Document Frequency (TF-IDF) converts textual strings into numerical vectors:
$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D)$$
Term Frequency measures how frequently word $t$ appears in headline $d$. Inverse Document Frequency downweights common filler words across all headlines $D$. We also include bigrams (`ngram_range=(1,2)`) to capture context such as "net profit" or "sales drop."

#### Q9: Why did you choose Multinomial Logistic Regression over a Deep Learning model?
**Answer:** For a lightweight, low-latency microservice with a demonstration dataset, Logistic Regression offers deterministic training, explainable coefficient weights, sub-millisecond CPU inference latency, zero GPU dependencies, and a serialized model artifact under 200 KB.

#### Q10: What accuracy did your model achieve and why is it honest?
**Answer:** On the held-out 20% stratified test split (36 headlines: 12 positive, 12 negative, 12 neutral), the model achieves exactly **61.11% test accuracy** with a macro F1-score of **0.5935**. We report real empirical metrics produced by `train.py`, rather than fabricating artificial 99% figures.

---

### Group C: Code Quality, Testing & Formatting

#### Q11: What is the purpose of Pytest in CI/CD?
**Answer:** Pytest automates unit and integration testing. In our project, 20 test cases validate route status codes, input boundaries, error response shapes, probability normalization, and model fixture serialization. Running `pytest --junitxml=reports/junit.xml` creates machine-readable reports for CI test summaries.

#### Q12: Why run `python -m compileall` and `python -m pip check`?
**Answer:** `compileall` checks Python syntax across all modules ahead of time without executing them, catching syntax errors immediately. `pip check` inspects the installed package tree to verify that there are no broken dependencies or conflicting sub-dependencies.

#### Q13: Why is Black used with `--check` in the CI pipeline?
**Answer:** Black is an opinionated, PEP 8-compliant code formatter. Running `black --check .` acts as a deterministic formatting gate in CI, failing the build if any developer pushes code that violates team formatting rules.

---

### Group D: Docker Container Packaging (Experiment 4)

#### Q14: Explain the Multi-Stage build pattern used in your Dockerfile.
**Answer:** Our Dockerfile separates build dependencies from the runtime image:
- Stage 1 (`builder`): Installs pip build tools, downloads production packages into `/opt/venv`, and executes `train.py` to bake `model.joblib`.
- Stage 2 (`runtime`): Starts from a clean `python:3.12-slim` image, copies only `/opt/venv`, the trained model, and application source code. All build tools, caches, and training artifacts are discarded.

#### Q15: Why is running containers as non-root critical for cloud security?
**Answer:** By default, Docker containers run as `root` (UID 0), which matches root on the host Linux kernel. If an attacker discovers an application exploit or container escape vulnerability, running as root grants them root access to the host node. Running as `UID 10001` restricts access strictly to the containerized application directory.

#### Q16: Why did you use Python standard library for HEALTHCHECK instead of `curl`?
**Answer:** Minimal base images (`python:3.12-slim`) do not include `curl` by default. Installing `curl` via `apt-get` bloats the image and introduces external binary dependencies with their own CVEs. Running `python -c "import urllib.request; urllib.request.urlopen(...)"` uses the native Python runtime already present, maintaining a zero-additional-footprint attack surface.

#### Q17: What is the role of Gunicorn in the Docker container?
**Answer:** Flask's built-in server is a single-threaded development server not designed for production concurrency or resource management. Gunicorn is a production-grade WSGI HTTP server using a pre-fork worker model (we configure 2 workers) to handle concurrent requests safely.

#### Q18: What is the purpose of `.dockerignore`?
**Answer:** `.dockerignore` prevents unnecessary files (such as local `.git`, virtual environments `venv/`, tests, temporary caches, and reports) from being sent as the build context to the Docker daemon. This speeds up build times and prevents confidential files or local test files from being accidentally baked into container layers.

---

### Group E: Security Scanners & Policies (Experiment 8)

#### Q19: What does Gitleaks scan and how does it detect secrets?
**Answer:** Gitleaks scans commit histories and the working directory using regular expressions and Shannon entropy analysis to detect high-entropy strings matching patterns for AWS keys, GitHub Personal Access Tokens, private RSA keys, and API credentials.

#### Q20: Why must Gitleaks run with `fetch-depth: 0` in CI?
**Answer:** A default `git checkout` in CI performs a shallow clone (`fetch-depth: 1`), downloading only the latest commit. If a developer accidentally committed a secret 3 commits ago and reverted it in the latest commit, a shallow scan would miss it. `fetch-depth: 0` clones full commit history, ensuring secrets buried in past commits are caught.

#### Q21: What is Checkov and what did it scan in this project?
**Answer:** Checkov is a static code analysis tool for Infrastructure as Code (IaC). In our project, Checkov scans both our `Dockerfile` and our GitHub Actions workflow `.github/workflows/devsecops.yml`, checking for container security misconfigurations (e.g. missing `USER`, missing `HEALTHCHECK`, unpinned base images, or improper pipeline permissions).

#### Q22: What is Aqua Trivy and what was your gate policy?
**Answer:** Trivy is a comprehensive vulnerability scanner. It scans Linux OS packages (Debian) and Python dependencies for known CVEs. Our gate policy was:
`--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`
This fails the CI pipeline if any High or Critical vulnerability exists that has an official upstream vendor patch available.

#### Q23: Why do we use `--ignore-unfixed` in the Trivy gate?
**Answer:** Unfixed vulnerabilities have no patch released by OS or package maintainers. Failing a deployment gate on an unfixable vulnerability would block releases indefinitely without actionable remediation. Focusing on fixable CVEs provides actionable security hygiene.

---

### Group F: GitHub Actions & GHCR Publishing (Experiment 13)

#### Q24: What is the trigger configuration in `devsecops.yml`?
**Answer:** The workflow triggers on:
- `push` to the `main` branch.
- `pull_request` to the `main` branch.
- `workflow_dispatch` (manual trigger via GitHub web UI).

#### Q25: Why do we set top-level `permissions: contents: read`?
**Answer:** This enforces the Principle of Least Privilege. By default, older GitHub Actions tokens possessed broad write access. Explicitly declaring `contents: read` at the top restricts the default token, granting `packages: write` only to the specific job (`publish-ghcr`) that actually publishes container images.

#### Q26: What does concurrency control accomplish in GitHub Actions?
**Answer:** 
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
If a developer pushes a new commit while an earlier pipeline run on the same branch is still executing, concurrency cancels the obsolete run, saving runner minutes and preventing race conditions in deployment.

#### Q27: How does Job 3 reuse the image from Job 2 without rebuilding?
**Answer:** Job 2 executes `docker save` and compresses the scanned image into a `.tar.gz` artifact uploaded via `actions/upload-artifact`. Job 3 downloads this artifact using `actions/download-artifact` and loads it via `docker load`. This guarantees that the exact bytes scanned by Trivy are what gets published to GHCR.

#### Q28: What is GitHub Container Registry (GHCR) and how do images get tagged?
**Answer:** GHCR (`ghcr.io`) is GitHub's OCI-compliant container registry. We authenticate using the automated `secrets.GITHUB_TOKEN` and tag the image with three identifiers:
1. `main` (branch identifier)
2. `${{ github.sha }}` (immutable 7-character commit SHA for rollback tracking)
3. `latest` (convenience pointer to the most recent verified build)

#### Q29: Why is publishing to GHCR restricted strictly to `push` on `main`?
**Answer:** Pull requests represent untrusted, unmerged code proposals that may originate from forks or feature branches. Allowing pull requests to publish images to GHCR would contaminate the production registry with unverified, experimental images.

#### Q30: How does the web dashboard track GitHub Actions status?
**Answer:** The `/api/pipeline-status` endpoint queries GitHub's REST API (`/actions/workflows/devsecops.yml/runs`) using the repository name. It maps job conclusions (`success` &rarr; `passed`, `failure` &rarr; `failed`) to the 7 status cards and caches the response in memory for 60 seconds to avoid GitHub API rate limits.

---

### Group G: Advanced Operational & Viva Edge Cases

#### Q31: What is the difference between a False Positive and a False Negative in security scans?
**Answer:** A False Positive flags non-vulnerable code or benign test keys as security vulnerabilities. A False Negative fails to detect an actual vulnerability or real leaked secret. In security, False Negatives are far more dangerous because they allow active vulnerabilities into production.

#### Q32: Why did we write comparison Dockerfiles in `demo/`?
**Answer:** `demo/Dockerfile.single-stage` demonstrates the concrete image size penalty of single-stage builds for the lab report, while `demo/Dockerfile.insecure` allows examiners to observe real Checkov and Trivy policy violations without weakening the production `Dockerfile`.

#### Q33: How does the application handle port conflicts on port 5000?
**Answer:** The application reads an optional `PORT` environment variable (`os.environ.get("PORT", 5000)`). If port 5000 is occupied by another local service (or macOS AirPlay), the user can launch on port 5001 via `$env:PORT="5001"; python app.py` or `docker run -p 5001:5000`.

#### Q34: What is the significance of the `GITHUB_STEP_SUMMARY` file in GitHub Actions?
**Answer:** `GITHUB_STEP_SUMMARY` is an environment file where GitHub Actions workflows can write Markdown content. Our pipeline writes an automated verification summary table, test results, and published image digests directly to the GitHub Actions workflow run page.

#### Q35: If the ML model needs to be updated with new data, what is the exact DevSecOps workflow?
**Answer:** The data scientist updates `data/headlines.csv` in a git branch, commits, and opens a Pull Request. CI automatically runs tests and quality checks. When merged to `main`, Job 2 rebuilds the multi-stage image (baking the new model during Stage 1), verifies it against Trivy and smoke tests, and publishes the new image with the new commit SHA to GHCR.

---

## Part 3: 5 Tricky Evaluator Questions (With Bulletproof Answers)

### Tricky Question 1:
> *"Why did you bake the ML model into the Docker image instead of downloading it from an S3 bucket or HuggingFace during container startup?"*

**Bulletproof Answer:**
> *"Downloading model weights at container startup introduces three major production failure modes:*
> 1. *It requires external network egress and AWS/cloud credentials at runtime, violating the principle of least privilege.*
> 2. *It slows down cold-start times during container restarts or auto-scaling events.*
> 3. *It breaks container immutability: if the remote S3 object changes or the HuggingFace API goes down, the container fails to start.*
> *By baking the model in the Docker builder stage, the container image becomes completely self-contained, reproducible, and verifiable by vulnerability scanners before deployment."*

---

### Tricky Question 2:
> *"What if your training dataset has an extreme class imbalance? How does that affect your pipeline?"*

**Bulletproof Answer:**
> *"Extreme class imbalance causes models to simply predict the majority class while reporting deceptively high accuracy.*
> *In our project, we addressed this in three ways:*
> 1. *We engineered a balanced demonstration dataset with exactly 60 positive, 60 negative, and 60 neutral headlines.*
> 2. *In `train.py`, we used `stratify=df['label']` in `train_test_split` to ensure every train/test fold preserves the exact class distribution.*
> 3. *We evaluate the model using macro-averaged F1-scores and a per-class classification report rather than relying solely on raw accuracy."*

---

### Tricky Question 3:
> *"Your Trivy scan passes today with zero vulnerabilities. Can the exact same container image fail Trivy next week without any code changes?"*

**Bulletproof Answer:**
> *"Yes, absolutely! Vulnerability databases (NVD / CVE) are updated continuously as new security flaws are discovered in existing software. An image scanned today might contain a package with a zero-day vulnerability that gets cataloged next Tuesday.*
> *This is why continuous DevSecOps practices mandate scheduled recurring scans (e.g. nightly cron workflows in GitHub Actions) on published registry images, rather than scanning only at the moment of git push."*

---

### Tricky Question 4:
> *"If an attacker sends a 10-megabyte string to `/predict`, what happens to your Flask server?"*

**Bulletproof Answer:**
> *"Our application enforces defensive input validation in `app.py`:*
> 1. *It validates Content-Type and trims whitespace.*
> 2. *It strictly rejects any input over 500 characters with an immediate `HTTP 400 Bad Request` before calling vectorizer transforms.*
> 3. *In production behind Gunicorn and reverse proxies (like Nginx), `client_max_body_size` is capped to reject oversized payloads at the network layer, preventing denial-of-service (DoS) memory exhaustion."*

---

### Tricky Question 5:
> *"Why did you use `USER 10001:10001` in your Dockerfile instead of just `USER appuser`?"*

**Bulletproof Answer:**
> *"Using the explicit numeric UID:GID (`10001:10001`) is a Kubernetes and container runtime best practice:*
> 1. *Container engines (like Docker, containerd, and Kubernetes Admission Controllers) can verify that the user is non-root purely from image metadata without needing to parse the container's `/etc/passwd` file.*
> 2. *Security policies such as Kubernetes `MustRunAsNonRoot` or Pod Security Standards inspect the numeric UID. If a named user has UID 0, a named check could be misled, whereas numeric UID 10001 provides an unambiguous, verifiable unprivileged identity."*
