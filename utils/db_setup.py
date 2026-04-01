"""
utils/db_setup.py
Initializes pharmacy_claims.db with the audited_claims table.
Run directly to create or reset the database.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "pharmacy_claims.db"

DDL = """
CREATE TABLE IF NOT EXISTS audited_claims (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id         TEXT    NOT NULL,
    member_id        TEXT,
    prescriber_npi   TEXT,
    ndc              TEXT,
    drug_name        TEXT,
    quantity         REAL,
    days_supply      INTEGER,
    daw_code         INTEGER,
    fill_date        TEXT,
    written_date     TEXT,
    claim_type       TEXT,
    override_code    TEXT,
    passed           INTEGER NOT NULL DEFAULT 0,  -- 1 = passed, 0 = failed
    error_count      INTEGER NOT NULL DEFAULT 0,
    errors_json      TEXT,                        -- full errors array as JSON
    healed_claim_json TEXT,                       -- full healed claim as JSON
    inserted_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create the database and table if they don't already exist."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(DDL)
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_db()
    conn.close()
    print(f"Database ready: {DB_PATH}")
