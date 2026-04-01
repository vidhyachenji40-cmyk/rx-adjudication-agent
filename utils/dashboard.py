"""
utils/dashboard.py
Connects to pharmacy_claims.db and prints an ASCII summary dashboard.
"""

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "pharmacy_claims.db"


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

Q_OVERALL = """
SELECT
    COUNT(*)                                  AS total_claims,
    SUM(passed)                               AS passed_claims,
    SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) AS failed_claims,
    ROUND(SUM(passed) * 100.0 / COUNT(*), 1) AS pass_rate_pct
FROM audited_claims;
"""

Q_BY_ERROR = """
SELECT
    json_each.value AS error_code,
    COUNT(*)        AS occurrences
FROM
    audited_claims,
    json_each(audited_claims.errors_json)
WHERE passed = 0
GROUP BY error_code
ORDER BY occurrences DESC;
"""

Q_RECENT = """
SELECT
    claim_id,
    prescriber_npi,
    ndc,
    CASE WHEN passed = 1 THEN 'PASS' ELSE 'FAIL' END AS status,
    error_count,
    inserted_at
FROM audited_claims
ORDER BY inserted_at DESC
LIMIT 10;
"""


# ---------------------------------------------------------------------------
# ASCII table helpers
# ---------------------------------------------------------------------------

def _col_widths(headers: list[str], rows: list[tuple]) -> list[int]:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell) if cell is not None else "NULL"))
    return widths


def _divider(widths: list[int]) -> str:
    return "+-" + "-+-".join("-" * w for w in widths) + "-+"


def _row_line(cells: list, widths: list[int]) -> str:
    parts = [str(c).ljust(w) if c is not None else "NULL".ljust(w) for c, w in zip(cells, widths)]
    return "| " + " | ".join(parts) + " |"


def ascii_table(title: str, headers: list[str], rows: list[tuple]) -> str:
    if not rows:
        return f"\n  {title}\n  (no data)\n"

    widths = _col_widths(headers, rows)
    div    = _divider(widths)
    total_width = sum(widths) + 3 * len(widths) + 1

    lines = [
        "",
        f"  {title}",
        div,
        _row_line(headers, widths),
        div,
        *[_row_line(row, widths) for row in rows],
        div,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dashboard sections
# ---------------------------------------------------------------------------

def section_overall(conn: sqlite3.Connection) -> str:
    row = conn.execute(Q_OVERALL).fetchone()
    if not row or row[0] == 0:
        return "\n  OVERALL SUMMARY\n  (no claims in database)\n"

    total, passed, failed, rate = row
    headers = ["Total Claims", "Passed", "Failed", "Pass Rate (%)"]
    return ascii_table("OVERALL SUMMARY", headers, [(total, passed, failed, rate)])


def section_errors(conn: sqlite3.Connection) -> str:
    rows = conn.execute(Q_BY_ERROR).fetchall()

    # extract the error_code value from the JSON object each row returns
    parsed = []
    for r in rows:
        cell = r[0]
        # json_each returns the whole JSON object; pull error_code field if needed
        try:
            import json
            obj = json.loads(cell)
            code = obj.get("error_code", cell)
        except Exception:
            code = cell
        parsed.append((code, r[1]))

    return ascii_table("FAILED CLAIMS BY ERROR CODE", ["Error Code", "Occurrences"], parsed)


def section_recent(conn: sqlite3.Connection) -> str:
    rows = conn.execute(Q_RECENT).fetchall()
    headers = ["Claim ID", "Prescriber NPI", "NDC", "Status", "Errors", "Inserted At"]
    return ascii_table("10 MOST RECENT CLAIMS", headers, rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def print_dashboard(db_path: Path = DB_PATH):
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    banner = "\n" + "=" * 66 + "\n  PHARMACY CLAIMS AUDIT DASHBOARD\n" + "=" * 66
    print(banner)
    print(section_overall(conn))
    print(section_errors(conn))
    print(section_recent(conn))
    print()

    conn.close()


if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    print_dashboard(db)
