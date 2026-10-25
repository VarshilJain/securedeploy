# DevSecOps Security Scan Reports Directory

This directory stores automated vulnerability, static analysis, and secret scanning reports generated during local execution and CI/CD pipelines.

## Security Tooling Overview

| Scanner | Target | Gate Policy | Generated Output |
| :--- | :--- | :--- | :--- |
| **Trivy** (Aqua Security) | Container Image & Dockerfile | Fail on `HIGH,CRITICAL` fixable CVEs (`--ignore-unfixed --exit-code 1`) | `reports/trivy-image-report.txt`<br>`reports/trivy-config-report.txt` |
| **Checkov** (Palo Alto / Bridgecrew) | Dockerfile & GitHub Actions YAML | Zero high severity misconfigurations (`--framework dockerfile,github_actions`) | `reports/checkov-report.txt`<br>`reports/checkov-report.json` |
| **Gitleaks** (Zachary Rice) | Git history & current working tree | Zero leaked credentials or high-entropy tokens (`--redact`) | `reports/gitleaks-report.json`<br>`reports/gitleaks-report.txt` |

## Gate Criteria & Remediation

1. **Trivy Image Scan**:
   - Scans Linux packages (Debian 12 Bookworm base) and Python dependencies.
   - Any CVE with severity `HIGH` or `CRITICAL` that has an official patch released must be remediated before publishing to GHCR.
   - Command: `trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 securedeploy:local`

2. **Checkov IaC Scan**:
   - Verifies security best practices for containers: non-root execution (`USER 10001`), explicit `HEALTHCHECK`, specific base image tags (`python:3.12-slim`), and avoiding insecure instructions like `ADD`.
   - Command: `checkov -f Dockerfile --framework dockerfile`

3. **Gitleaks Secret Scan**:
   - Inspects regex patterns and Shannon entropy to detect leaked API keys, tokens, and private keys.
   - Command: `gitleaks detect --source . --verbose --redact`

## Report Retention
All individual `*.json`, `*.txt`, and `*.sarif` files inside this folder are ignored by Git (`.gitignore`) to keep the repository clean. Only this `README.md` is committed.
