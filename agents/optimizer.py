"""
Pharmacy Claim Optimizer
Reads JSON audit output from validator.py and raises Manager Alerts
for INVALID_NPI or NDC_NOT_FOUND errors, with suggested SQL queries
to investigate the affected Prescriber NPI across all claims.
"""

import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Alert triggers
# ---------------------------------------------------------------------------

ALERT_TRIGGERS = {"INVALID_NPI", "NDC_NOT_FOUND"}

ALERT_DESCRIPTIONS = {
    "INVALID_NPI": (
        "Prescriber NPI failed registry validation. "
        "The NPI may be inactive, unregistered, or incorrectly transcribed."
    ),
    "NDC_NOT_FOUND": (
        "NDC could not be matched in the drug formulary. "
        "The drug may be unlisted, recalled, or the NDC may be malformed."
    ),
}


# ---------------------------------------------------------------------------
# SQL suggestion builder
# ---------------------------------------------------------------------------

def suggest_npi_sql(prescriber_npi: str, error_code: str) -> str:
    """Return a SQL query to pull all claims for the flagged prescriber NPI."""
    return f"""
-- Manager Alert Query: All claims associated with Prescriber NPI {prescriber_npi}
-- Triggered by error: {error_code}
SELECT
    c.claim_id,
    c.member_id,
    c.prescriber_npi,
    c.ndc,
    c.drug_name,
    c.quantity,
    c.days_supply,
    c.fill_date,
    c.written_date,
    c.claim_type,
    c.claim_status,
    c.paid_amount
FROM
    claims c
WHERE
    c.prescriber_npi = '{prescriber_npi}'
ORDER BY
    c.fill_date DESC;
""".strip()


# ---------------------------------------------------------------------------
# Alert printer
# ---------------------------------------------------------------------------

def print_manager_alert(claim_id: str, prescriber_npi: str, error_code: str, message: str):
    divider = "=" * 70
    print(divider)
    print("  *** MANAGER ALERT ***")
    print(divider)
    print(f"  Claim ID        : {claim_id}")
    print(f"  Error Code      : {error_code}")
    print(f"  Prescriber NPI  : {prescriber_npi}")
    print(f"  Detail          : {message}")
    print(f"  Reason          : {ALERT_DESCRIPTIONS.get(error_code, 'See error detail above.')}")
    print()
    print("  Suggested SQL to investigate all claims for this prescriber:")
    print()
    for line in suggest_npi_sql(prescriber_npi, error_code).splitlines():
        print(f"    {line}")
    print(divider)
    print()


# ---------------------------------------------------------------------------
# Core processor
# ---------------------------------------------------------------------------

def process_audit_results(audit_results: list[dict]):
    """
    Scan a list of AuditResult summary dicts (from validator.audit_claims_batch)
    and fire Manager Alerts for any INVALID_NPI or NDC_NOT_FOUND errors.
    """
    alerts_fired = 0

    for result in audit_results:
        claim_id = result.get("claim_id", "UNKNOWN")
        prescriber_npi = result.get("prescriber_npi") or result.get(
            "healed_claim", {}
        ).get("prescriber_npi", "UNKNOWN")

        for error in result.get("errors", []):
            code = error.get("error_code", "")
            if code in ALERT_TRIGGERS:
                print_manager_alert(
                    claim_id=claim_id,
                    prescriber_npi=prescriber_npi,
                    error_code=code,
                    message=error.get("message", ""),
                )
                alerts_fired += 1

    if alerts_fired == 0:
        print("No Manager Alerts triggered. All claims cleared INVALID_NPI and NDC_NOT_FOUND checks.")
    else:
        print(f"Total Manager Alerts fired: {alerts_fired}")


# ---------------------------------------------------------------------------
# Entry point — reads JSON from a file path arg or stdin
# ---------------------------------------------------------------------------

def load_results(source: str | None) -> list[dict]:
    if source:
        path = Path(source)
        if not path.exists():
            print(f"Error: file not found: {source}", file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # Accept either a single result dict or a list
    if isinstance(data, dict):
        data = [data]
    return data


if __name__ == "__main__":
    source_file = sys.argv[1] if len(sys.argv) > 1 else None
    results = load_results(source_file)
    process_audit_results(results)
