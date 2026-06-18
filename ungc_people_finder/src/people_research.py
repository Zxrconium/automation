"""Find People/HR executives at a company."""
import logging
import re
from typing import List, Optional, Tuple

from src.search import BaseSearchProvider
from src.scoring import match_role, TARGET_ROLES
from src.validators import normalize_url

logger = logging.getLogger("ungc.people")

# Regex to extract person names (2-4 capitalized words)
NAME_RE = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b')

TITLE_KEYWORDS = [
    "chief people", "chief human resources", "chief hr", "chro",
    "people & culture", "people and culture", "head of people",
    "hr director", "human resources director", "people director",
    "talent director", "chief talent", "employee experience",
    "head of hr", "vp people", "vice president people",
    "general manager people", "director of people", "director people",
    "executive general manager people", "chief culture",
    "chief workforce", "workplace director",
]

def _contains_target_title(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in TITLE_KEYWORDS)

def _extract_candidates(text: str) -> List[Tuple[str, str]]:
    """
    Extract (name, title) pairs from text.
    Uses a sliding-window heuristic: find a title keyword, look nearby for a name.
    """
    candidates = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        for kw in TITLE_KEYWORDS:
            if kw in line_lower:
                title = line.strip()
                # Look ±3 lines for a name
                window = lines[max(0, i-3):i+4]
                for wl in window:
                    names = NAME_RE.findall(wl)
                    for name in names:
                        if len(name.split()) >= 2 and name != title:
                            candidates.append((name, title))
                break
    return candidates


def research_people(
    company_name: str,
    domain: Optional[str],
    search: BaseSearchProvider,
) -> Tuple[Optional[str], Optional[str], int, str, List[str]]:
    """
    Returns (person_name, person_title, role_score, role_match_type, source_urls).
    """
    queries = []

    if domain:
        queries += [
            f'site:{domain} "Chief People Officer"',
            f'site:{domain} "People and Culture"',
            f'site:{domain} "Chief Human Resources Officer"',
            f'site:{domain} "Leadership" "People"',
            f'site:{domain} "Executive Team" "People"',
        ]

    queries += [
        f'"{company_name}" "Chief People Officer"',
        f'"{company_name}" "People and Culture" executive',
        f'"{company_name}" "Head of People and Culture"',
        f'"{company_name}" "HR Director"',
        f'"{company_name}" "Chief Human Resources Officer"',
        f'"{company_name}" "Executive General Manager People"',
        f'"{company_name}" "General Manager People and Culture"',
        f'"{company_name}" "Director People and Culture"',
    ]

    best_name: Optional[str] = None
    best_title: Optional[str] = None
    best_score: int = 0
    best_match_type: str = "none"
    source_urls: List[str] = []

    for query in queries:
        try:
            results = search.search(query, num_results=5)
            for r in results:
                source_urls.append(normalize_url(r.url))
                text = r.title + "\n" + r.snippet
                if not _contains_target_title(text):
                    continue

                candidates = _extract_candidates(text)
                for name, title in candidates:
                    matched_role, score, match_type = match_role(title)
                    if score > best_score:
                        best_name = name
                        best_title = title
                        best_score = score
                        best_match_type = match_type
                        logger.info(f"  Found candidate: {name} | {title} | score={score}")

                # Also try simple title extraction if no structured pair found
                if not candidates and _contains_target_title(text):
                    names = NAME_RE.findall(text)
                    for name in names:
                        if len(name.split()) >= 2:
                            # Guess title from text
                            for kw_title, kw_score in TARGET_ROLES:
                                if kw_title.lower() in text.lower():
                                    if kw_score > best_score:
                                        best_name = name
                                        best_title = kw_title
                                        best_score = kw_score
                                        best_match_type = "keyword"
                                        break

        except Exception as e:
            logger.warning(f"People search error for {company_name}: {e}")

    # Deduplicate sources
    unique_sources = list(dict.fromkeys(s for s in source_urls if s))[:10]
    return best_name, best_title, best_score, best_match_type, unique_sources
