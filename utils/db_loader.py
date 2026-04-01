"""
utils/db_loader.py
Reads audit results JSON and inserts healed claim records into pharmacy_claims.db.

Usage:
    python utils/db_loader.py <audit_results.json>
    python utils/db_loader.py          # reads from stdin
"""

import json
import sqlite3
import sys
from pathlib import Path

# Resolve paths relative to the project root (parent of utils/)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "pharmacy_claims.db"

sys.path.insert(0, str(BASE_DIR))
from utils.db_setup import init_db


INSERT_SQL = """
INSERT INTO audited_claims (
    claim_id, member_id, prescriber_npi, ndc, drug_name,
    quantity, days_supply, daw_code, fill_date, written_date,
    claim_type, override_code,
    passed, error_count, errors_json, healed_claim_json
) VALUES (
    :claim_id, :member_id, :prescriber_npi, :ndc, :drug_name,
    :quantity, :days_supply, :daw_code, :fill_date, :written_date,
    :claim_type, :override_code,
    :passed, :error_count, :errors_json, :healed_claim_json
);
"""


def _row(result: dict) -> dict:
    """Flatten an AuditResult summary dict into a DB row."""
    healed = result.get("healed_claim") or {}
    return {
        "claim_id":          result.get("claim_id", "UNKNOWN"),
        "member_id":         healed.get("member_id") or result.get("member_id"),
        "prescriber_npi":    healed.get("prescriber_npi") or result.get("prescriber_npi"),
        "ndc":               healed.get("ndc"),
        "drug_name":         healed.get("drug_name"),
        "quantity":          healed.get("quantity"),
        "days_supply":       healed.get("days_supply"),
        "daw_code":          healed.get("daw_code"),
        "fill_date":         healed.get("fill_date"),
        "written_date":      healed.get("written_date"),
        "claim_type":        healed.get("claim_type"),
        "override_code":     healed.get("override_code"),
        "passed":            1 if result.get("passed") else 0,
        "error_count":       result.get("error_count", 0),
        "errors_json":       json.dumps(result.get("errors", [])),
        "healed_claim_json": json.dumps(healed) if healed else None,
    }


def load_results(audit_results: list[dict], db_path: Path = DB_PATH) -> int:
    """Insert all audit results into the DB. Returns number of rows inserted."""
    conn = init_db(db_path)
    rows = [_row(r) for r in audit_results]
    with conn:
        conn.executemany(INSERT_SQL, rows)
    conn.close()
    return len(rows)


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else None
    if source:
        path = Path(source)
        if not path.exists():
            print(f"Error: file not found: {source}", file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    if isinstance(data, dict):
        data = [data]

    inserted = load_results(data)
    print(f"Inserted {inserted} audit record(s) into {DB_PATH}")


if __name__ == "__main__":
    main()
