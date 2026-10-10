import pandas as pd
import pytest

from jobmarket.dashboard import make_charts
from jobmarket.eligibility import is_eligible
from jobmarket.match import match_job
from jobmarket.storage import market_summary, top_companies, top_skills


@pytest.mark.parametrize("location,title,expected", [
    ("Worldwide", "Junior Python Developer", True),
    ("Remote", "Software Engineer", True),
    ("Remote, APAC", "Support Engineer (APAC)", True),
    ("Remote, Global", "Platform Security Engineer (AMER/APAC)", True),  # mixed region incl. APAC
    ("Remote, US", "Software Engineer L2", False),
    ("US", "Backend Developer", False),                                  # Standalone US
    ("US (Remote)", "Software Engineer", False),                         # US Remote
    ("Remote - India", "Data Analyst", True),                            # candidate IS in India
    ("Remote, Canada", "Backend Engineer", False),
    ("East Coast US & Europe (Remote)", "Software Engineer", False),
    ("Remote, Global", "Support Engineer (EMEA - Weekends)", False),     # title narrows region
    ("Berlin, Germany", "Python Developer", False),
])
def test_eligibility(location, title, expected):
    assert is_eligible(location, title) is expected


def test_match_scores_family_and_seniority():
    junior = match_job("Junior Backend Developer",
                       "Python SQL FastAPI postgres docker git rest api")
    senior = match_job("Senior Backend Engineer",
                       "Python SQL FastAPI postgres docker git rest api 8+ years")
    assert junior.family == "python_dev"
    assert junior.score > senior.score  # seniority penalty must bite
    assert "python" in junior.skills_matched


def test_match_detects_genai_family():
    res = match_job("AI Engineer (Agentic Systems)",
                    "Build LLM applications, RAG pipelines, CrewAI agents, OpenAI and Gemini APIs")
    assert res.family == "genai_ai"
    assert res.score >= 8


def test_match_caps_keyword_stuffing():
    stuffed = match_job("Marketing Associate", " ".join(["python sql llm rag etl aws gcp docker"] * 30))
    lean = match_job("Marketing Associate", "python sql llm rag etl aws gcp docker")
    # stuffing may still nudge the family classification a little, but it must
    # never dominate: skill score is capped and per-pattern hits are capped at 2
    assert stuffed.score - lean.score <= 3


def test_word_boundary_skill_matching_avoids_false_positives():
    # Ordinary English words containing short skill substrings
    text = "We offer cloud storage, digital marketing campaigns, and client interest."
    res = match_job("Operations Manager", text)
    # Must NOT match rag (from storage), git (from digital), rest (from interest)
    assert "rag" not in res.skills_matched
    assert "git" not in res.skills_matched
    assert "rest" not in res.skills_matched


def test_market_summary_and_top_skills():
    df = pd.DataFrame([
        {"source": "remoteok", "company": "Acme", "family": "python_dev", "match_score": 9.0,
         "skills_matched": "python,sql,docker"},
        {"source": "remoteok", "company": "Beta", "family": "python_dev", "match_score": 6.0,
         "skills_matched": "python"},
        {"source": "himalayas", "company": "Acme", "family": "data_ml", "match_score": 8.2,
         "skills_matched": "python,tensorflow"},
    ])
    s = market_summary(df)
    assert s["postings"] == 3 and s["companies"] == 2 and s["strong_matches"] == 2
    assert top_skills(df).idxmax() == "python"
    assert top_companies(df).idxmax() == "Acme"


def test_empty_dataframe_handling(tmp_path):
    empty_df = pd.DataFrame(columns=["source", "company", "family", "match_score", "skills_matched"])
    s = market_summary(empty_df)
    assert s["postings"] == 0
    assert s["companies"] == 0
    assert s["median_score"] == 0.0
    charts = make_charts(empty_df, tmp_path)
    assert charts == []
