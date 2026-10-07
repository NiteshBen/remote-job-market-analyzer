"""Fetch job postings from public remote-job APIs and RSS feeds.

Every source here is a documented public endpoint. Sources that require a
login (LinkedIn, Indeed) are deliberately excluded.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, text/xml, application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class Job:
    source: str
    title: str
    company: str
    location: str
    url: str
    tags: list = field(default_factory=list)
    description: str = ""
    date: str = ""
    salary: str = ""
    job_type: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _clean_html(text: str | None) -> str:
    import html as _html

    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def fetch_remoteok() -> list[Job]:
    data = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=40).json()
    out = []
    for j in data:
        if not isinstance(j, dict) or "position" not in j:
            continue  # first element is a legal notice
        url = j.get("url", "")
        out.append(Job(
            source="remoteok",
            title=j.get("position", ""),
            company=j.get("company") or "",
            location=j.get("location") or "Worldwide",
            url=url if url.startswith("http") else "https://remoteok.com" + url,
            tags=j.get("tags") or [],
            description=(j.get("description") or "")[:4000],
            date=j.get("date") or "",
            job_type=j.get("type") or "",
        ))
    return out


def fetch_remotive(limit: int = 50) -> list[Job]:
    data = requests.get(
        f"https://remotive.com/api/remote-jobs?limit={limit}", headers=HEADERS, timeout=40
    ).json()
    return [
        Job(
            source="remotive",
            title=j.get("title", ""),
            company=j.get("company_name") or "",
            location=j.get("candidate_required_location") or "Worldwide",
            url=j.get("url") or "",
            tags=j.get("tags") or [],
            description=_clean_html(j.get("description"))[:4000],
            date=j.get("publication_date") or "",
            salary=j.get("salary") or "",
            job_type=j.get("job_type") or "",
        )
        for j in data.get("jobs", [])
    ]


def fetch_jobicy() -> list[Job]:
    out = []
    for url in (
        "https://jobicy.com/api/v2/remote-jobs?count=50",
        "https://jobicy.com/api/v2/remote-jobs?count=50&industry=Cybersecurity",
    ):
        try:
            data = requests.get(url, headers=HEADERS, timeout=40).json()
        except requests.RequestException:
            continue
        for j in data.get("jobs", []):
            out.append(Job(
                source="jobicy",
                title=j.get("jobTitle", ""),
                company=j.get("companyName") or "",
                location=j.get("jobGeo") or "Worldwide",
                url=j.get("url") or "",
                tags=[j.get("jobLevel") or "", j.get("jobIndustry") or ""],
                description=_clean_html(j.get("jobExcerpt"))[:2000],
                date=j.get("pubDate") or "",
                job_type=j.get("jobType") or "",
            ))
    return out


def fetch_himalayas(pages: int = 5) -> list[Job]:
    """Himalayas exposes offset pagination on their public jobs endpoint."""
    out = []
    for offset in range(0, pages * 50, 50):
        try:
            data = requests.get(
                f"https://himalayas.app/jobs/api?limit=50&offset={offset}",
                headers=HEADERS, timeout=40,
            ).json()
        except requests.RequestException:
            break
        batch = data.get("jobs", [])
        if not batch:
            break
        for j in batch:
            sal = None
            if j.get("minSalary"):
                sal = f'{j["minSalary"]}-{j.get("maxSalary", "")} {j.get("currency", "")}'
            out.append(Job(
                source="himalayas",
                title=j.get("title", ""),
                company=j.get("companyName") or "",
                location=", ".join(j.get("locationRestrictions") or []) or "Worldwide",
                url=j.get("applicationLink") or j.get("guid") or "",
                tags=(j.get("categories") or []) + (j.get("seniority") or []),
                description=_clean_html(j.get("description"))[:5000],
                date=j.get("postedAt") or "",
                salary=sal or "",
                job_type=j.get("employmentType") or "",
            ))
    return out


def fetch_workingnomads() -> list[Job]:
    data = requests.get(
        "https://www.workingnomads.com/api/exposed_jobs/", headers=HEADERS, timeout=40
    ).json()
    return [
        Job(
            source="workingnomads",
            title=j.get("title", ""),
            company=j.get("company_name") or "",
            location=j.get("location") or "Worldwide",
            url=j.get("url") or j.get("apply_url") or "",
            tags=[j.get("category_name") or ""],
            description=_clean_html(j.get("description"))[:3000],
            date=j.get("pub_date") or "",
            job_type=j.get("job_type") or "",
        )
        for j in data
    ]


WWR_FEEDS = {
    "programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "data": "https://weworkremotely.com/categories/remote-data-jobs.rss",
    "design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "devops": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
}


def fetch_weworkremotely() -> list[Job]:
    out = []
    for cat, url in WWR_FEEDS.items():
        try:
            root = ET.fromstring(requests.get(url, headers=HEADERS, timeout=40).content)
        except (requests.RequestException, ET.ParseError):
            continue
        for item in root.iter("item"):
            get = lambda tag: (item.find(tag).text or "") if item.find(tag) is not None else ""
            title = get("title")
            company, _, rest = title.partition(":")
            out.append(Job(
                source="weworkremotely",
                title=rest.strip() or title,
                company=company.strip(),
                location="Worldwide (see listing)",
                url=get("link"),
                tags=[cat],
                description=_clean_html(get("description"))[:3000],
                date=get("pubDate"),
            ))
    return out


def fetch_arbeitnow() -> list[Job]:
    out = []
    for page in (1, 2):
        data = requests.get(
            f"https://www.arbeitnow.com/api/job-board-api?page={page}",
            headers=HEADERS, timeout=40,
        ).json()
        for j in data.get("data", []):
            if not j.get("remote"):
                continue
            out.append(Job(
                source="arbeitnow",
                title=j.get("title", ""),
                company=j.get("company_name") or "",
                location=j.get("location") or "Remote",
                url=j.get("url") or "",
                tags=j.get("tags") or [],
                description=_clean_html(j.get("description"))[:3000],
            ))
    return out


FETCHERS = {
    "remoteok": fetch_remoteok,
    "remotive": fetch_remotive,
    "jobicy": fetch_jobicy,
    "himalayas": fetch_himalayas,
    "workingnomads": fetch_workingnomads,
    "weworkremotely": fetch_weworkremotely,
    "arbeitnow": fetch_arbeitnow,
}


def fetch_all(sources: list[str] | None = None) -> list[Job]:
    """Fetch from the given sources (default: all), tolerating individual failures."""
    picked = [FETCHERS[s] for s in (sources or FETCHERS)]
    jobs: list[Job] = []
    for fn in picked:
        try:
            jobs.extend(fn())
        except Exception as exc:  # one dead API must not kill the run
            print(f"[warn] {fn.__name__}: {exc}")
    return dedupe(jobs)


def dedupe(jobs: list[Job]) -> list[Job]:
    seen: set[tuple[str, str]] = set()
    out = []
    for j in jobs:
        key = (_norm(j.title)[:70], _norm(j.company))
        if not j.title or key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


def _norm(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"\b(inc|ltd|llc|gmbh|corp|corporation|company|co)\b\.?", "", text)
    return re.sub(r"[^a-z0-9]", "", text)
