# RX Adjudication Agent

An end-to-end pharmacy claims adjudication pipeline built in Python and PowerShell. The system validates incoming claims, flags bad data, auto-heals correctable errors, fires manager alerts for critical violations, persists results to a SQLite database, and renders a live ASCII dashboard — all from a single command.

---

## Pipeline Overview

```
sample_claims.json
       │
       ▼
┌─────────────────┐
│  1. VALIDATION  │  agents/validator.py
│                 │  • NPI format check (10-digit NPPES)
│                 │  • Dosage math correction (healer logic)
│                 │  • Flags: INVALID_NPI, NDC_NOT_FOUND
└────────┬────────┘
         │ audit results (JSON)
         ▼
┌─────────────────┐
│ 2. OPTIMIZATION │  agents/optimizer.py
│                 │  • Scans for INVALID_NPI / NDC_NOT_FOUND
│                 │  • Prints Manager Alerts with prescriber context
│                 │  • Suggests SQL queries for investigator follow-up
└────────┬────────┘
         │ alert output
         ▼
┌─────────────────┐
│  3. REPORTING   │  run_audit.ps1
│                 │  • Saves daily_audit_YYYYMMDD.txt to reports/
│                 │  • Timestamped header + full alert transcript
└────────┬────────┘
         │ healed JSON results
         ▼
┌─────────────────┐
│  4. DB LOADING  │  utils/db_loader.py + utils/db_setup.py
│                 │  • Initializes pharmacy_claims.db (SQLite, WAL mode)
│                 │  • Inserts all audited claims with pass/fail status
│                 │  • Stores full error JSON and healed claim per row
└────────┬────────┘
         │ database
         ▼
┌─────────────────┐
│ 5. DASHBOARDING │  utils/dashboard.py
│                 │  • Overall summary: total / passed / failed / pass rate
│                 │  • Error frequency breakdown by code
│                 │  • 10 most recent claims with live PASS/FAIL status
└─────────────────┘
```

---

## Project Structure

```
Adjudication-Flow/
├── agents/
│   ├── validator.py       # Stage 1 — claim validation & healer logic
│   └── optimizer.py       # Stage 2 — manager alert engine
├── utils/
│   ├── db_setup.py        # SQLite schema initializer
│   ├── db_loader.py       # Stage 4 — bulk insert audit results
│   └── dashboard.py       # Stage 5 — ASCII terminal dashboard
├── data/
│   └── sample_claims.json # Input claims (NCPDP-style fields)
├── run_audit.ps1          # Orchestrator — runs all 5 stages end to end
└── README.md
```

---

## Quick Start

**Requirements:** Python 3.10+, PowerShell 5+

```powershell
# Run the full pipeline
.\run_audit.ps1
```

That single command will:
1. Validate all claims in `data/sample_claims.json`
2. Print Manager Alerts for any `INVALID_NPI` or `NDC_NOT_FOUND` errors
3. Save a dated text report to `reports/daily_audit_YYYYMMDD.txt`
4. Insert all audit records into `pharmacy_claims.db`
5. Print the live dashboard to the terminal

---

## Running Individual Stages

```bash
# Validate claims and print raw audit JSON
python -c "
import json, sys
sys.path.insert(0, '.')
from agents.validator import audit_claims_batch
with open('data/sample_claims.json') as f:
    claims = json.load(f)
print(json.dumps(audit_claims_batch(claims), indent=2))
"

# Run the optimizer against a saved results file
python agents/optimizer.py reports/audit_results_YYYYMMDD.json

# Initialize or reset the database
python utils/db_setup.py

# Load a results file into the database
python utils/db_loader.py reports/audit_results_YYYYMMDD.json

# View the dashboard at any time
python utils/dashboard.py
```

---

## Claim Fields

| Field | Type | Description |
|---|---|---|
| `claim_id` | string | Unique claim identifier |
| `member_id` | string | Insurance member ID |
| `prescriber_npi` | string | 10-digit NPI (NPPES) |
| `ndc` | string | National Drug Code |
| `drug_name` | string | Human-readable drug name |
| `quantity` | number | Units dispensed |
| `daily_dosage` | number | Units per day (used for days supply math) |
| `days_supply` | integer | Days the fill should last |
| `fill_date` | YYYY-MM-DD | Date the prescription was filled |
| `written_date` | YYYY-MM-DD | Date the prescription was written |
| `claim_type` | string | NCPDP transaction type (B1/B2/B3) |

---

## Manager Alert Triggers

| Error Code | Trigger | Action |
|---|---|---|
| `INVALID_NPI` | Prescriber NPI is not 10 digits | Manager Alert + SQL query for all claims from that NPI |
| `NDC_NOT_FOUND` | NDC field contains `NDC_NOT_FOUND` sentinel | Manager Alert + SQL query for all claims from that prescriber |

---

## Database Schema

```sql
CREATE TABLE audited_claims (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id          TEXT,
    member_id         TEXT,
    prescriber_npi    TEXT,
    ndc               TEXT,
    drug_name         TEXT,
    quantity          REAL,
    days_supply       INTEGER,
    daw_code          INTEGER,
    fill_date         TEXT,
    written_date      TEXT,
    claim_type        TEXT,
    override_code     TEXT,
    passed            INTEGER,   -- 1 = PASS, 0 = FAIL
    error_count       INTEGER,
    errors_json       TEXT,      -- JSON array of error objects
    healed_claim_json TEXT,      -- Full healed claim as JSON
    inserted_at       TEXT
);
```

---

## Tech Stack

- **Python 3.10+** — pipeline logic, SQLite via `sqlite3`, JSON via `json`
- **PowerShell 5+** — orchestration (`run_audit.ps1`)
- **SQLite** — lightweight embedded database (WAL mode)
- No external Python dependencies — stdlib only
