"""Excel dashboard + charts from the analyzed postings."""
from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")  # headless-safe
import matplotlib.pyplot as plt  # noqa: E402

ACCENT = "#1F3B63"


def make_charts(df: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if df.empty:
        return []
    paths = []

    # 1) postings by role family
    fam = df["family"].value_counts().head(8)
    ax = fam.sort_values().plot(kind="barh", figsize=(8, 4.5), color=ACCENT)
    ax.set_title("Eligible worldwide-remote postings by role family")
    ax.set_xlabel("postings")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    p = out_dir / "postings_by_family.png"
    ax.figure.tight_layout()
    ax.figure.savefig(p, dpi=130)
    plt.close(ax.figure)
    paths.append(p)

    # 2) most-demanded skills
    from .storage import top_skills

    skills = top_skills(df)
    if not skills.empty:
        ax = skills.sort_values().plot(kind="barh", figsize=(8, 5), color="#2E7D52")
        ax.set_title("Skills demanded across eligible postings")
        ax.set_xlabel("postings mentioning the skill")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        p = out_dir / "top_skills.png"
        ax.figure.tight_layout()
        ax.figure.savefig(p, dpi=130)
        plt.close(ax.figure)
        paths.append(p)

    # 3) match-score distribution
    ax = df["match_score"].clip(lower=-5).plot(
        kind="hist", bins=30, figsize=(8, 4), color=ACCENT, edgecolor="white")
    ax.set_title("Match-score distribution (resume vs postings)")
    ax.set_xlabel("match score")
    ax.axvline(8, color="#C0392B", linestyle="--", linewidth=1.2)
    ax.text(8.2, ax.get_ylim()[1] * 0.85, "strong match (>=8)", color="#C0392B", fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    p = out_dir / "match_scores.png"
    ax.figure.tight_layout()
    ax.figure.savefig(p, dpi=130)
    plt.close(ax.figure)
    paths.append(p)

    return paths


def make_excel_dashboard(df: pd.DataFrame, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    from openpyxl.styles import Alignment, Font, PatternFill

    cols = ["match_score", "title", "company", "family", "skills_matched", "location",
            "salary", "source", "date", "url"]
    if df.empty:
        df = pd.DataFrame(columns=cols)
    else:
        df = df.sort_values("match_score", ascending=False)[cols]
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Eligible", index=False)
        df[df["match_score"] >= 8].to_excel(writer, sheet_name="Strong Matches", index=False)
        for sheet in writer.sheets.values():
            for cell in sheet[1]:
                cell.fill = PatternFill("solid", fgColor="1F3B63")
                cell.font = Font(color="FFFFFF", bold=True)
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            sheet.freeze_panes = "A2"
            widths = [10, 42, 24, 16, 30, 24, 16, 18, 11, 46]
            for i, w in enumerate(widths, 1):
                sheet.column_dimensions[chr(64 + i)].width = w
    return out_path
