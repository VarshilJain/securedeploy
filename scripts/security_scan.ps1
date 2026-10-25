# ==============================================================================
# SecureDeploy ML - Local Security Scanning Automation (PowerShell / Windows)
# Experiment 8: DevSecOps Automation with Trivy, Checkov, and Gitleaks
# Cloud Computing Lab DJS23ALMD701
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ImageTag = "securedeploy:local",
    [switch]$SkipImageScan = $false
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReportsDir = Join-Path $ProjectRoot "reports"

if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   SecureDeploy ML - Automated Security Scanning Suite   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"
Write-Host "Reports Directory: $ReportsDir"
Write-Host ""

$OverallStatus = 0
$Summary = @()

# ------------------------------------------------------------------------------
# 1. Gitleaks - Secret Detection Scan
# ------------------------------------------------------------------------------
Write-Host "[1/3] Running Gitleaks Secret Detection..." -ForegroundColor Yellow
$GitleaksReportText = Join-Path $ReportsDir "gitleaks-report.txt"
$GitleaksReportJson = Join-Path $ReportsDir "gitleaks-report.json"

if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
    & gitleaks detect --source $ProjectRoot --verbose --redact --report-path $GitleaksReportJson > $GitleaksReportText 2>&1
    $GitleaksExit = $LASTEXITCODE
    if ($GitleaksExit -eq 0) {
        Write-Host "  [+] Gitleaks: PASSED (0 secrets detected)" -ForegroundColor Green
        $Summary += [PSCustomObject]@{ Scanner = "Gitleaks"; Gate = "Secrets Leak Gate"; Status = "PASSED" }
    } else {
        Write-Host "  [!] Gitleaks: FAILED (Secrets detected or syntax error, see $GitleaksReportText)" -ForegroundColor Red
        $Summary += [PSCustomObject]@{ Scanner = "Gitleaks"; Gate = "Secrets Leak Gate"; Status = "FAILED" }
        $OverallStatus = 1
    }
} else {
    Write-Host "  [-] Gitleaks: NOT INSTALLED. Install via: winget install gitleaks (or choco install gitleaks)" -ForegroundColor Yellow
    $Summary += [PSCustomObject]@{ Scanner = "Gitleaks"; Gate = "Secrets Leak Gate"; Status = "NOT RUN (Missing Binary)" }
}

Write-Host ""

# ------------------------------------------------------------------------------
# 2. Checkov - Infrastructure as Code (IaC) Scan
# ------------------------------------------------------------------------------
Write-Host "[2/3] Running Checkov Static Analysis on Dockerfile & Workflow..." -ForegroundColor Yellow
$CheckovReportText = Join-Path $ReportsDir "checkov-report.txt"
$CheckovReportJson = Join-Path $ReportsDir "checkov-report.json"

if (Get-Command checkov -ErrorAction SilentlyContinue) {
    & checkov -d $ProjectRoot --framework dockerfile,github_actions --output cli --output json --output-file-path "console,$CheckovReportJson" > $CheckovReportText 2>&1
    $CheckovExit = $LASTEXITCODE
    if ($CheckovExit -eq 0) {
        Write-Host "  [+] Checkov: PASSED (0 policy violations)" -ForegroundColor Green
        $Summary += [PSCustomObject]@{ Scanner = "Checkov"; Gate = "IaC Security Gate"; Status = "PASSED" }
    } else {
        Write-Host "  [!] Checkov: FAILED (Policy violations detected, see $CheckovReportText)" -ForegroundColor Red
        $Summary += [PSCustomObject]@{ Scanner = "Checkov"; Gate = "IaC Security Gate"; Status = "FAILED" }
        $OverallStatus = 1
    }
} else {
    Write-Host "  [-] Checkov: NOT INSTALLED. Install via: pip install checkov" -ForegroundColor Yellow
    $Summary += [PSCustomObject]@{ Scanner = "Checkov"; Gate = "IaC Security Gate"; Status = "NOT RUN (Missing Binary)" }
}

Write-Host ""

# ------------------------------------------------------------------------------
# 3. Trivy - Misconfiguration and Container Vulnerability Scan
# ------------------------------------------------------------------------------
Write-Host "[3/3] Running Trivy Scans..." -ForegroundColor Yellow
$TrivyConfigReport = Join-Path $ReportsDir "trivy-config-report.txt"
$TrivyImageReport = Join-Path $ReportsDir "trivy-image-report.txt"

if (Get-Command trivy -ErrorAction SilentlyContinue) {
    # 3a. Trivy Config Scan
    Write-Host "  Scanning Dockerfile and repository configuration..."
    & trivy config $ProjectRoot --exit-code 1 --severity HIGH,CRITICAL > $TrivyConfigReport 2>&1
    $TrivyConfigExit = $LASTEXITCODE

    if ($TrivyConfigExit -eq 0) {
        Write-Host "  [+] Trivy Config: PASSED" -ForegroundColor Green
        $Summary += [PSCustomObject]@{ Scanner = "Trivy Config"; Gate = "Misconfig Gate"; Status = "PASSED" }
    } else {
        Write-Host "  [!] Trivy Config: FAILED (High/Critical misconfigs found, see $TrivyConfigReport)" -ForegroundColor Red
        $Summary += [PSCustomObject]@{ Scanner = "Trivy Config"; Gate = "Misconfig Gate"; Status = "FAILED" }
        $OverallStatus = 1
    }

    # 3b. Trivy Image Scan (if requested and Docker is available)
    if (-not $SkipImageScan) {
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            Write-Host "  Scanning container image: $ImageTag..."
            & trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 $ImageTag > $TrivyImageReport 2>&1
            $TrivyImageExit = $LASTEXITCODE

            if ($TrivyImageExit -eq 0) {
                Write-Host "  [+] Trivy Image: PASSED (0 fixable HIGH/CRITICAL CVEs)" -ForegroundColor Green
                $Summary += [PSCustomObject]@{ Scanner = "Trivy Image"; Gate = "CVE Gate"; Status = "PASSED" }
            } else {
                Write-Host "  [!] Trivy Image: FAILED (Fixable vulnerabilities found, see $TrivyImageReport)" -ForegroundColor Red
                $Summary += [PSCustomObject]@{ Scanner = "Trivy Image"; Gate = "CVE Gate"; Status = "FAILED" }
                $OverallStatus = 1
            }
        } else {
            Write-Host "  [-] Docker not available. Skipping container image scan." -ForegroundColor Yellow
            $Summary += [PSCustomObject]@{ Scanner = "Trivy Image"; Gate = "CVE Gate"; Status = "NOT RUN (No Docker)" }
        }
    }
} else {
    Write-Host "  [-] Trivy: NOT INSTALLED. Install via: winget install aqua-security.trivy (or choco install trivy)" -ForegroundColor Yellow
    $Summary += [PSCustomObject]@{ Scanner = "Trivy"; Gate = "Vulnerability Gate"; Status = "NOT RUN (Missing Binary)" }
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "                 SCAN SUMMARY REPORT                      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
$Summary | Format-Table -AutoSize

if ($OverallStatus -ne 0) {
    Write-Host "[!] Security Scan Gate FAILED. Inspect reports in $ReportsDir." -ForegroundColor Red
    exit 1
} else {
    Write-Host "[+] All executed security gates PASSED." -ForegroundColor Green
    exit 0
}
