"""SQLite storage for fetched postings, plus pandas-based market analysis."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT, title TEXT, company TEXT, location TEXT, url TEXT UNIQUE,
    tags TEXT, description TEXT, date TEXT, salary TEXT, job_type TEXT,
    eligible INTEGER, family TEXT, match_score REAL, skills_matched TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_family ON jobs(family);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    return con


def save_jobs(con: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert rows (dicts with the Job fields + eligibility/match columns).

    UNIQUE(url) makes re-runs idempotent: existing postings are skipped.
    """
    before = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    con.executemany(
        """INSERT OR IGNORE INTO jobs
           (source, title, company, location, url, tags, description, date, salary,
            job_type, eligible, family, match_score, skills_matched)
           VALUES (:source, :title, :company, :location, :url, :tags, :description,
                   :date, :salary, :job_type, :eligible, :family, :match_score,
                   :skills_matched)""",
        rows,
    )
    con.commit()
    after = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    return after - before


def load_frame(con: sqlite3.Connection, eligible_only: bool = True) -> pd.DataFrame:
    query = "SELECT * FROM jobs" + (" WHERE eligible = 1" if eligible_only else "")
    return pd.read_sql_query(query, con)


def market_summary(df: pd.DataFrame) -> dict:
    """Headline numbers for the README/dashboard."""
    return {
        "postings": len(df),
        "companies": int(df["company"].nunique()),
        "sources": df["source"].nunique(),
        "by_family": df["family"].value_counts().head(8).to_dict(),
        "strong_matches": int((df["match_score"] >= 8).sum()),
        "median_score": round(float(df["match_score"].median()), 2),
    }


def top_skills(df: pd.DataFrame, n: int = 15) -> pd.Series:
    """Most-demanded skills across eligible postings (skills_matched column)."""
    counts: dict[str, int] = {}
    for cell in df["skills_matched"].dropna():
        for skill in str(cell).split(","):
            skill = skill.strip()
            if skill:
                counts[skill] = counts.get(skill, 0) + 1
    return pd.Series(counts).sort_values(ascending=False).head(n)


def top_companies(df: pd.DataFrame, n: int = 10) -> pd.Series:
    return df["company"].value_counts().head(n)
