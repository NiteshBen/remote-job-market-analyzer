"""Location eligibility: which postings can a candidate based in India actually take?

Rules are regex-driven and deliberately conservative — a wrongly-included listing
wastes an application, a wrongly-excluded one only hides a maybe.
"""
from __future__ import annotations

import re

# Regions/countries that cannot hire a candidate working from India.
_INELIGIBLE = [
    r"\bus[- ]?only\b", r"united states", r"\busa\b", r"\bu\.s\.", r"us citizen", r"\busc\b",
    r"\bcanada\b", r"canadian", r"\buk only\b", r"united kingdom", r"\bengland\b", r"\blondon\b",
    r"east coast", r"west coast", r"us[ /&+]*europe", r"usa[ /&+]*europe", r"europe[ /&+]*us",
    r"europe only", r"european union", r"\beu only\b", r"\bemea\b", r"\bamer\b", r"\blatam\b",
    r"\bnorth america\b", r"\bamericas\b",
    r"must (be|reside) (in|located) (the )?(us|europe)",
    r"germany", r"france", r"spain", r"netherlands", r"poland", r"portugal", r"romania",
    r"\bbelgium\b", r"\bitaly\b", r"austria", r"denmark", r"sweden", r"norway", r"finland",
    r"ireland", r"\bbrazil\b", r"mexico", r"colombia", r"argentina", r"\bchile\b", r"\bperu\b",
    r"ecuador", r"uruguay", r"costa rica", r"\bjapan\b", r"philippines", r"singapore",
    r"indonesia", r"vietnam", r"thailand", r"malaysia", r"pakistan", r"bangladesh", r"\bnepal\b",
    r"sri lanka", r"\buae\b", r"\bdubai\b", r"saudi", r"qatar", r"\bkenya\b", r"nigeria",
    r"south africa", r"\begypt\b", r"israel", r"turkey", r"ukraine", r"australia only",
    r"new zealand", r"remote[- ,]*(us|usa)\b", r"\bus remote\b", r"japanese speaking",
    r"right to work in", r"authorized to work in the us", r"no relocation",
    r"berlin", r"munich", r"amsterdam", r"paris", r"barcelona", r"madrid", r"dublin", r"warsaw",
]

_REGION_BLOCK_RE = re.compile("|".join(_INELIGIBLE), re.IGNORECASE)
# Titles like "(EMEA)" or "(AMER)" narrow the region even when the location field says "Remote".
_TITLE_REGION_RE = re.compile(r"\b(amer|emea|latam)\b|east coast|us[ /&+]*europe", re.IGNORECASE)
_TITLE_KEEP_RE = re.compile(r"\b(apac|asia|india|global|worldwide|anywhere)\b", re.IGNORECASE)


def is_eligible(location: str, title: str = "") -> bool:
    """True if a candidate working from India could take this posting."""
    loc = (location or "").lower()
    if not loc or loc in ("remote", "remote - worldwide", "worldwide", "anywhere"):
        loc_ok = True
    else:
        loc_ok = not _REGION_BLOCK_RE.search(loc)
    title = (title or "").lower()
    title_ok = not (_TITLE_REGION_RE.search(title) and not _TITLE_KEEP_RE.search(title))
    return loc_ok and title_ok
