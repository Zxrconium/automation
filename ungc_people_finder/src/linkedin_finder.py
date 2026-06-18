"""Find LinkedIn profile URLs via search API (no LinkedIn scraping)."""
import logging
import re
from typing import Optional, Tuple

from src.search import BaseSearchProvider
from src.validators import normalize_linkedin_url

logger = logging.getLogger("ungc.linkedin")

LINKEDIN_RE = re.compile(r'https?://(?:www\.)?linkedin\.com/in/[^/\s"\'<>]+', re.IGNORECASE)


def _extract_linkedin_url(text: str) -> Optional[str]:
    m = LINKEDIN_RE.search(text)
    if m:
        return normalize_linkedin_url(m.group(0))
    return None


def find_linkedin(
    person_name: str,
    company_name: str,
    person_title: str,
    search: BaseSearchProvider,
) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Returns (linkedin_url, confidence, source_url).
    Confidence: 'high', 'medium', 'low'
    """
    first, *rest = person_name.strip().split()
    last = rest[-1] if rest else ""

    queries = [
        (f'site:linkedin.com/in "{person_name}" "{company_name}"', "high"),
        (f'site:linkedin.com/in "{person_name}" "{person_title}"', "high"),
        (f'"{person_name}" "{company_name}" linkedin.com/in', "medium"),
        (f'"{person_name}" linkedin "{company_name}" Australia', "medium"),
    ]

    for query, expected_conf in queries:
        try:
            results = search.search(query, num_results=5)
            for r in results:
                # Check if result URL is a linkedin profile
                li_url = normalize_linkedin_url(r.url)
                if li_url:
                    # Verify name appears in snippet or title
                    combined = (r.title + " " + r.snippet).lower()
                    name_words = person_name.lower().split()
                    name_matches = sum(1 for w in name_words if w in combined)
                    if name_matches >= 2:
                        logger.info(f"LinkedIn found ({expected_conf}): {li_url}")
                        return li_url, expected_conf, r.url
                    elif name_matches >= 1 and last.lower() in combined:
                        logger.info(f"LinkedIn found (medium-low): {li_url}")
                        return li_url, "medium", r.url

                # Also check snippet for LinkedIn URL
                li_url = _extract_linkedin_url(r.snippet)
                if li_url and person_name.split()[-1].lower() in r.snippet.lower():
                    return li_url, "medium", r.url

        except Exception as e:
            logger.warning(f"LinkedIn search error: {e}")

    return None, "none", None
