"""Role matching and confidence scoring."""
import logging
from typing import Optional, Tuple, List
from rapidfuzz import fuzz, process

logger = logging.getLogger("ungc.scoring")

# Target roles with their base scores
TARGET_ROLES: List[Tuple[str, int]] = [
    ("Chief People Officer", 100),
    ("Chief Human Resources Officer", 100),
    ("CHRO", 100),
    ("Chief People & Culture Officer", 100),
    ("Chief People and Culture Officer", 100),
    ("Chief Talent Officer", 95),
    ("Chief Employee Experience Officer", 95),
    ("Executive General Manager People & Culture", 90),
    ("Executive General Manager People and Culture", 90),
    ("General Manager People & Culture", 88),
    ("General Manager People and Culture", 88),
    ("Head of People & Culture", 87),
    ("Head of People and Culture", 87),
    ("People and Culture Executive", 85),
    ("Director People & Culture", 84),
    ("Director of People and Culture", 84),
    ("VP People", 82),
    ("Vice President People", 82),
    ("HR Director", 80),
    ("Human Resources Director", 80),
    ("Director of Human Resources", 80),
    ("Head of HR", 78),
    ("Head of Human Resources", 78),
    ("People Director", 78),
    ("Culture Director", 75),
    ("Talent Director", 75),
    ("Workplace Director", 72),
    ("People Manager", 65),
    ("HR Manager", 60),
]

ROLE_NAMES = [r[0] for r in TARGET_ROLES]
ROLE_SCORES = {r[0]: r[1] for r in TARGET_ROLES}

def match_role(title: str) -> Tuple[str, int, str]:
    """
    Returns (matched_role, score, match_type).
    match_type: 'exact', 'fuzzy', 'none'
    """
    if not title:
        return "", 0, "none"

    title_lower = title.lower().strip()

    # Exact match
    for role, score in TARGET_ROLES:
        if role.lower() == title_lower:
            return role, score, "exact"

    # Fuzzy match
    match = process.extractOne(title, ROLE_NAMES, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= 75:
        matched_role = match[0]
        base_score = ROLE_SCORES[matched_role]
        # Penalize fuzzy matches slightly
        adjusted = int(base_score * (match[1] / 100) * 0.95)
        return matched_role, adjusted, "fuzzy"

    # Keyword match
    keywords = [
        ("people", 65), ("culture", 65), ("hr", 60), ("human resources", 65),
        ("talent", 65), ("workforce", 60), ("employee experience", 70),
    ]
    title_lower2 = title_lower
    for kw, score in keywords:
        if kw in title_lower2:
            return kw.title(), score, "keyword"

    return "", 0, "none"


def compute_confidence(
    domain_conf: float,
    role_score: int,
    has_linkedin: bool,
    linkedin_conf: Optional[str],
    has_confirmed_email: bool,
    has_potential_email: bool,
    source_count: int,
) -> int:
    """Compute overall 0-100 confidence score."""
    score = 0

    # Domain discovery (max 20)
    score += min(20, int(domain_conf * 20))

    # Person/role match (max 35)
    score += min(35, int(role_score * 0.35))

    # LinkedIn (max 20)
    if has_linkedin:
        li_scores = {"high": 20, "medium": 13, "low": 7}
        score += li_scores.get(linkedin_conf or "", 7)

    # Email (max 15)
    if has_confirmed_email:
        score += 15
    elif has_potential_email:
        score += 8

    # Source quality (max 10)
    score += min(10, source_count * 2)

    return min(100, score)
