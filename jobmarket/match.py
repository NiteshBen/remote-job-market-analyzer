"""Resume-to-job matching: skill overlap scoring and role-family classification."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Skills the candidate can honestly claim, weighted by how central they are.
# (For Nitesh: entry-level Python / AI / data profile.)
DEFAULT_SKILL_WEIGHTS: dict[str, float] = {
    "python": 5, "sql": 3, "pandas": 2, "numpy": 1.5, "tensorflow": 2.2, "pytorch": 2.2,
    "scikit-learn": 2, "power bi": 3.2, "powerbi": 3.2, "crewai": 4, "gemini": 2.5,
    "generative ai": 3, "genai": 3, "llm": 3, "machine learning": 3, "deep learning": 2.5,
    "data analysis": 2.5, "data science": 2.5, "ai agent": 3.5, "langchain": 2.5,
    "openai": 2, "chatgpt": 1.8, "java": 1.5, "c++": 1, "django": 1.8, "flask": 1.5,
    "fastapi": 1.8, "api": 1.5, "rest": 1, "git": 1, "docker": 1, "aws": 1, "azure": 0.8,
    "gcp": 0.8, "tableau": 1.5, "excel": 0.8, "dashboard": 1.5, "etl": 1.2,
    "analytics": 1.5, "visualization": 1.2, "automation": 1.2, "backend": 1.2,
    "testing": 1, "mongodb": 0.8, "postgres": 1, "mysql": 0.8, "nlp": 2,
    "computer vision": 1.8, "prompt": 1.8, "rag": 2.5,
}

FAMILIES: dict[str, list[str]] = {
    "genai_ai": [r"generative ai", r"\bllm", r"ai agent", r"prompt engineer", r"langchain",
                 r"crewai", r"\bopenai\b", r"\bgemini\b", r"\bchatgpt", r"ai trainer",
                 r"ai tutor", r"artificial intelligence", r"applied ai", r"ai engineer"],
    "data_analyst_bi": [r"data analyst", r"\banalytics\b", r"business intelligence", r"\bbi\b",
                        r"power bi", r"tableau", r"looker", r"dashboard", r"insights analyst",
                        r"data visualization"],
    "data_ml": [r"machine learning", r"\bml engineer", r"data scientist", r"deep learning",
                r"tensorflow", r"pytorch", r"\bnlp\b", r"computer vision", r"\bmlops\b",
                r"\bdata engineer", r"\betl\b"],
    "python_dev": [r"python developer", r"backend engineer", r"back-end", r"\bdjango\b",
                    r"\bflask\b", r"\bfastapi\b", r"software engineer", r"software developer",
                    r"\bpython\b"],
    "qa_testing": [r"\bqa\b", r"quality assurance", r"test engineer", r"\bsdet\b", r"\btester\b"],
    "support_solutions": [r"technical support", r"solutions engineer", r"support engineer",
                          r"customer engineer", r"technical consultant"],
    "design": [r"graphic designer", r"visual designer", r"\bui\b designer", r"\bux\b",
               r"web designer", r"creative designer"],
    "fullstack": [r"full[- ]?stack", r"\breact\b", r"front[- ]?end", r"javascript"],
}

_SENIORITY = [r"\bsenior\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b", r"\bhead of\b",
              r"\bdirector\b", r"\bmanager\b", r"\barchitect\b", r"\bsr\.?\b", r"\bvp\b",
              r"\bii\b", r"\biii\b", r"[5-9]\+? years", r"10\+ years"]
_JUNIOR = [r"\bjunior\b", r"entry[- ]level", r"\bgraduate\b", r"\btrainee\b", r"\bintern\b",
           r"early career", r"\bassociate\b"]


@dataclass
class MatchResult:
    score: float
    family: str
    skills_matched: list[str] = field(default_factory=list)
    seniority_penalty: float = 0.0
    junior_bonus: float = 0.0
    family_strength: float = 0.0


def _family_scores(title: str, text: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for fam, patterns in FAMILIES.items():
        s = 0.0
        for p in patterns:
            # cap per-pattern hits: a JD repeating "llm" 30 times is stuffing, not signal
            s += 3.0 * min(len(re.findall(p, title, re.I)), 2) \
               + 1.0 * min(len(re.findall(p, text[:3500], re.I)), 2)
        scores[fam] = s
    return scores


def _skill_matches(skill: str, text: str) -> bool:
    """Match skill keywords using word boundaries to prevent substring false-positives."""
    if skill in ("c++", "c#"):
        return skill in text
    return bool(re.search(r"\b" + re.escape(skill) + r"\b", text))


def match_job(job_title: str, job_text: str,
              skill_weights: dict[str, float] | None = None) -> MatchResult:
    """Score how well a posting fits the resume.

    score = capped skill overlap + capped family strength + junior bonus
            - seniority penalty. Positive >= 8 means a strong match.
    """
    weights = skill_weights or DEFAULT_SKILL_WEIGHTS
    title = job_title or ""
    text = (job_text or "").lower()
    title_low = title.lower()

    skill_score, matched = 0.0, []
    for skill, weight in weights.items():
        if _skill_matches(skill, text):
            skill_score += weight
            matched.append(skill)
    skill_score = min(skill_score, 12.0)  # cap: keyword-stuffed JDs shouldn't dominate

    fam_scores = _family_scores(title, text)
    family = max(fam_scores, key=fam_scores.get)
    family_strength = min(fam_scores.get(family, 0.0) * 0.8, 8.0)
    if fam_scores[family] < 2.0:
        family, family_strength = "other", 0.0

    penalty = 8.0 * sum(1 for p in _SENIORITY if re.search(p, title_low))
    penalty += 1.5 if any(re.search(p, text[:3000]) for p in (r"[5-9]\+? years",)) else 0.0
    bonus = 4.0 if any(re.search(p, title_low) for p in _JUNIOR) else 0.0

    total = skill_score + family_strength + bonus - penalty
    return MatchResult(score=round(total, 2), family=family, skills_matched=matched,
                       seniority_penalty=penalty, junior_bonus=bonus,
                       family_strength=family_strength)
