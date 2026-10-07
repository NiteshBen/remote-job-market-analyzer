"""Command-line interface.

    python cli.py fetch --db jobs.db
    python cli.py dashboard --db jobs.db --out output/
    python cli.py report --db jobs.db
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jobmarket.dashboard import make_charts, make_excel_dashboard
from jobmarket.eligibility import is_eligible
from jobmarket.fetch import fetch_all
from jobmarket.match import match_job
from jobmarket.storage import connect, load_frame, market_summary, save_jobs, top_companies, top_skills


def cmd_fetch(args: argparse.Namespace) -> None:
    con = connect(args.db)
    jobs = fetch_all()
    rows = []
    for j in jobs:
        m = match_job(j.title, " ".join(map(str, j.tags)) + " " + j.description)
        rows.append({**j.as_dict(), "tags": ",".join(map(str, j.tags)),
                     "eligible": int(is_eligible(j.location, j.title)),
                     "family": m.family, "match_score": m.score,
                     "skills_matched": ",".join(m.skills_matched)})
    added = save_jobs(con, rows)
    total = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"fetched {len(jobs)} postings, {added} new; database now holds {total}")


def cmd_dashboard(args: argparse.Namespace) -> None:
    con = connect(args.db)
    df = load_frame(con)
    charts = make_charts(df, args.out)
    xlsx = make_excel_dashboard(df, Path(args.out) / "dashboard.xlsx")
    print("charts:", ", ".join(str(c) for c in charts))
    print("dashboard:", xlsx)


def cmd_report(args: argparse.Namespace) -> None:
    con = connect(args.db)
    df = load_frame(con)
    summary = market_summary(df)
    print(json.dumps(summary, indent=2))
    print("\nTop demanded skills:")
    print(top_skills(df).to_string())
    print("\nCompanies hiring most remotely:")
    print(top_companies(df).to_string())
    print("\nTop 10 matches for the resume:")
    cols = ["match_score", "title", "company", "family", "location", "url"]
    with __import__("pandas").option_context("display.width", 200):
        print(df.sort_values("match_score", ascending=False)[cols].head(10).to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(prog="jobmarket",
                                 description="Analyze the worldwide-remote job market.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "dashboard", "report"):
        sp = sub.add_parser(name)
        sp.add_argument("--db", default="jobs.db", help="SQLite database file")
        if name == "dashboard":
            sp.add_argument("--out", default="output", help="output directory")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "dashboard": cmd_dashboard, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
