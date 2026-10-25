#!/usr/bin/env bash
# ==============================================================================
# SecureDeploy ML - Local Security Scanning Automation (Linux / macOS)
# Experiment 8: DevSecOps Automation with Trivy, Checkov, and Gitleaks
# Cloud Computing Lab DJS23ALMD701
# ==============================================================================

set -o pipefail

IMAGE_TAG="${1:-securedeploy:local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="${PROJECT_ROOT}/reports"

mkdir -p "$REPORTS_DIR"

echo "=========================================================="
echo "   SecureDeploy ML - Automated Security Scanning Suite   "
echo "=========================================================="
echo "Project Root: ${PROJECT_ROOT}"
echo "Reports Directory: ${REPORTS_DIR}"
echo ""

OVERALL_STATUS=0

# ------------------------------------------------------------------------------
# 1. Gitleaks - Secret Detection Scan
# ------------------------------------------------------------------------------
echo "[1/3] Running Gitleaks Secret Detection..."
GITLEAKS_REPORT_TXT="${REPORTS_DIR}/gitleaks-report.txt"
GITLEAKS_REPORT_JSON="${REPORTS_DIR}/gitleaks-report.json"

if command -v gitleaks &>/dev/null; then
    if gitleaks detect --source "$PROJECT_ROOT" --verbose --redact --report-path "$GITLEAKS_REPORT_JSON" > "$GITLEAKS_REPORT_TXT" 2>&1; then
        echo "  [+] Gitleaks: PASSED (0 secrets detected)"
    else
        echo "  [!] Gitleaks: FAILED (Secrets detected, see ${GITLEAKS_REPORT_TXT})"
        OVERALL_STATUS=1
    fi
else
    echo "  [-] Gitleaks: NOT INSTALLED. Install via: brew install gitleaks (or download binary)"
fi

echo ""

# ------------------------------------------------------------------------------
# 2. Checkov - Infrastructure as Code (IaC) Scan
# ------------------------------------------------------------------------------
echo "[2/3] Running Checkov Static Analysis on Dockerfile & Workflow..."
CHECKOV_REPORT_TXT="${REPORTS_DIR}/checkov-report.txt"
CHECKOV_REPORT_JSON="${REPORTS_DIR}/checkov-report.json"

if command -v checkov &>/dev/null; then
    if checkov -d "$PROJECT_ROOT" --framework dockerfile,github_actions --output cli --output json --output-file-path "console,${CHECKOV_REPORT_JSON}" > "$CHECKOV_REPORT_TXT" 2>&1; then
        echo "  [+] Checkov: PASSED (0 policy violations)"
    else
        echo "  [!] Checkov: FAILED (Violations detected, see ${CHECKOV_REPORT_TXT})"
        OVERALL_STATUS=1
    fi
else
    echo "  [-] Checkov: NOT INSTALLED. Install via: pip install checkov"
fi

echo ""

# ------------------------------------------------------------------------------
# 3. Trivy - Misconfiguration and Vulnerability Scan
# ------------------------------------------------------------------------------
echo "[3/3] Running Trivy Scans..."
TRIVY_CONFIG_REPORT="${REPORTS_DIR}/trivy-config-report.txt"
TRIVY_IMAGE_REPORT="${REPORTS_DIR}/trivy-image-report.txt"

if command -v trivy &>/dev/null; then
    echo "  Scanning repository config and Dockerfile..."
    if trivy config "$PROJECT_ROOT" --exit-code 1 --severity HIGH,CRITICAL > "$TRIVY_CONFIG_REPORT" 2>&1; then
        echo "  [+] Trivy Config: PASSED"
    else
        echo "  [!] Trivy Config: FAILED (High/Critical issues found, see ${TRIVY_CONFIG_REPORT})"
        OVERALL_STATUS=1
    fi

    if command -v docker &>/dev/null; then
        echo "  Scanning container image: ${IMAGE_TAG}..."
        if trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "$IMAGE_TAG" > "$TRIVY_IMAGE_REPORT" 2>&1; then
            echo "  [+] Trivy Image: PASSED (0 fixable HIGH/CRITICAL CVEs)"
        else
            echo "  [!] Trivy Image: FAILED (Fixable vulnerabilities found, see ${TRIVY_IMAGE_REPORT})"
            OVERALL_STATUS=1
        fi
    else
        echo "  [-] Docker not available. Skipping container image scan."
    fi
else
    echo "  [-] Trivy: NOT INSTALLED. Install via: brew install trivy (or apt-get install trivy)"
fi

echo ""
echo "=========================================================="
if [ $OVERALL_STATUS -ne 0 ]; then
    echo "[!] Security scan gate FAILED. Inspect reports in ${REPORTS_DIR}"
    exit 1
else
    echo "[+] All executed security gates PASSED."
    exit 0
fi
