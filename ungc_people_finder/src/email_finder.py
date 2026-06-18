"""Find confirmed and potential emails."""
import logging
import re
import time
from typing import List, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.search import BaseSearchProvider
from src.email_pattern import extract_emails_from_text, infer_pattern, build_potential_email, PatternResult
from src.validators import is_valid_email_syntax, check_mx, normalize_url
from src import cache as cache_module

logger = logging.getLogger("ungc.email")

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def _fetch_page(url: str) -> str:
    cached = cache_module.get(f"page:{url}", settings.cache_ttl_hours)
    if cached:
        return cached
    time.sleep(settings.request_delay)
    headers = {"User-Agent": settings.user_agent}
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 200:
                cache_module.set(f"page:{url}", r.text)
                return r.text
    except Exception as e:
        logger.debug(f"Fetch error {url}: {e}")
    return ""


def _search_for_emails(
    query: str,
    search: BaseSearchProvider,
    domain: str,
    person_name: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Search and return list of (email, source_url)."""
    found = []
    try:
        results = search.search(query, num_results=5)
        for r in results:
            text = r.title + " " + r.snippet
            emails = extract_emails_from_text(text, domain)
            for e in emails:
                if is_valid_email_syntax(e):
                    if person_name:
                        name_parts = person_name.lower().split()
                        if any(p in e.lower() for p in name_parts):
                            found.append((e, normalize_url(r.url)))
                    else:
                        found.append((e, normalize_url(r.url)))
    except Exception as ex:
        logger.warning(f"Email search error: {ex}")
    return found


def find_emails(
    person_name: Optional[str],
    company_name: str,
    domain: str,
    search: BaseSearchProvider,
) -> Tuple[
    Optional[str], Optional[str],   # confirmed_email, confirmed_source
    Optional[PatternResult],         # pattern
    List[str],                       # other_emails
]:
    """
    Returns (confirmed_email, confirmed_source_url, email_pattern, other_emails_list).
    """
    if not domain:
        return None, None, None, []

    confirmed: Optional[str] = None
    confirmed_source: Optional[str] = None
    all_domain_emails: List[Tuple[str, str]] = []

    # Build search queries
    queries = []
    if person_name:
        first = person_name.split()[0] if person_name else ""
        last = person_name.split()[-1] if person_name else ""
        queries += [
            (f'site:{domain} "{person_name}" "@{domain}"', True),
            (f'site:{domain} "{first}" "{last}" email', True),
            (f'"{person_name}" "@{domain}"', True),
        ]

    queries += [
        (f'site:{domain} "People and Culture" "@{domain}"', False),
        (f'site:{domain} "media contact" "@{domain}"', False),
        (f'site:{domain} "contact" "@{domain}"', False),
        (f'site:{domain} email contact', False),
    ]

    for query, person_specific in queries:
        pairs = _search_for_emails(query, search, domain, person_name if person_specific else None)
        for email, source in pairs:
            all_domain_emails.append((email, source))
            if person_specific and not confirmed and person_name:
                name_parts = [p.lower() for p in person_name.split() if len(p) > 1]
                if any(p in email.lower() for p in name_parts):
                    confirmed = email
                    confirmed_source = source
                    logger.info(f"Confirmed email found: {email}")

    # Deduplicate other emails
    unique_emails = list(dict.fromkeys(e for e, _ in all_domain_emails))
    other_emails = [e for e in unique_emails if e != confirmed]

    # Infer pattern
    pattern: Optional[PatternResult] = None
    if unique_emails:
        pattern = infer_pattern(unique_emails, domain)
        if pattern:
            logger.info(f"Email pattern found: {pattern.pattern_name} (e.g. {pattern.example})")

    return confirmed, confirmed_source, pattern, other_emails[:5]


def build_potential(
    person_name: Optional[str],
    domain: str,
    pattern: Optional[PatternResult],
) -> Optional[str]:
    if not person_name or not pattern:
        return None
    parts = person_name.strip().split()
    if len(parts) < 2:
        return None
    first = parts[0]
    last = parts[-1]
    email = build_potential_email(first, last, domain, pattern)
    if email and is_valid_email_syntax(email):
        return email
    return None
