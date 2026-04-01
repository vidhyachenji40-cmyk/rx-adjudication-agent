# run_audit.ps1
# Runs the pharmacy audit pipeline:
#   1. validator.py   — audits data/sample_claims.json
#   2. optimizer.py   — scans for INVALID_NPI / NDC_NOT_FOUND, prints Manager Alerts
#   3. Saves output   — reports/daily_audit_YYYYMMDD.txt
#   4. db_loader.py   — inserts healed results into pharmacy_claims.db

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Paths (all relative to the project root)
# ---------------------------------------------------------------------------
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaimsFile   = Join-Path $ScriptDir "data\sample_claims.json"
$ValidatorPy  = Join-Path $ScriptDir "agents\validator.py"
$OptimizerPy  = Join-Path $ScriptDir "agents\optimizer.py"
$DbLoaderPy   = Join-Path $ScriptDir "utils\db_loader.py"
$DashboardPy  = Join-Path $ScriptDir "utils\dashboard.py"
$ReportsDir   = Join-Path $ScriptDir "reports"
$DateStamp    = Get-Date -Format "yyyyMMdd"
$ReportFile   = Join-Path $ReportsDir "daily_audit_$DateStamp.txt"
$ResultsJson  = Join-Path $ReportsDir "audit_results_$DateStamp.json"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
foreach ($path in @($ClaimsFile, $ValidatorPy, $OptimizerPy, $DbLoaderPy, $DashboardPy)) {
    if (-not (Test-Path $path)) {
        Write-Error "Required file not found: $path"
        exit 1
    }
}

if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir | Out-Null
}

# ---------------------------------------------------------------------------
# Step 1 & 2: validator -> optimizer (alerts to screen + text report)
# Write runner to a temp file to avoid PowerShell here-string escaping issues
# ---------------------------------------------------------------------------
$TempAudit = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.py'
@'
import sys, json
sys.path.insert(0, sys.argv[1])
from agents.validator import audit_claims_batch
from agents.optimizer import process_audit_results

with open(sys.argv[2], "r", encoding="utf-8") as f:
    claims = json.load(f)

results = audit_claims_batch(claims)
process_audit_results(results)
'@ | Set-Content -Path $TempAudit -Encoding utf8

# ---------------------------------------------------------------------------
# Step 3: dump healed JSON results for the DB loader
# ---------------------------------------------------------------------------
$TempJson = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.py'
@'
import sys, json
sys.path.insert(0, sys.argv[1])
from agents.validator import audit_claims_batch

with open(sys.argv[2], "r", encoding="utf-8") as f:
    claims = json.load(f)

results = audit_claims_batch(claims)

with open(sys.argv[3], "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
'@ | Set-Content -Path $TempJson -Encoding utf8

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
Write-Host "Running pharmacy audit for $DateStamp ..."
Write-Host "Claims file : $ClaimsFile"
Write-Host "Report file : $ReportFile"
Write-Host "Database    : $(Join-Path $ScriptDir 'pharmacy_claims.db')"
Write-Host ""

# Capture alert output for the text report
$Output = python $TempAudit $ScriptDir $ClaimsFile 2>&1

# Write JSON results file for the DB loader
python $TempJson $ScriptDir $ClaimsFile $ResultsJson 2>&1 | Out-Null

Remove-Item $TempAudit, $TempJson -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# Save text report
# ---------------------------------------------------------------------------
$Header = @"
================================================================================
  DAILY PHARMACY AUDIT REPORT
  Date      : $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  Claims    : $ClaimsFile
================================================================================

"@

($Header + ($Output -join "`n")) | Out-File -FilePath $ReportFile -Encoding utf8

# ---------------------------------------------------------------------------
# Step 4: Load healed results into SQLite
# ---------------------------------------------------------------------------
$DbOutput = python $DbLoaderPy $ResultsJson 2>&1

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host $Output
Write-Host ""
Write-Host "Report saved : $ReportFile"
Write-Host $DbOutput

# ---------------------------------------------------------------------------
# Step 5: Dashboard summary
# ---------------------------------------------------------------------------
python $DashboardPy 2>&1
