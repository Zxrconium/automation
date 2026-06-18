"""Discover official company website/domain."""
import logging
import re
import time
from typing import Optional, Tuple
from urllib.parse import urlparse

import tldextract
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.search import BaseSearchProvider

logger = logging.getLogger("ungc.domain")

# Domains to reject (directories, social, job boards, news)
REJECT_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "seek.com.au", "indeed.com", "glassdoor.com", "au.indeed.com",
    "wikipedia.org", "bloomberg.com", "crunchbase.com", "yelp.com",
    "yellowpages.com.au", "abr.business.gov.au", "asx.com.au",
    "abc.net.au", "smh.com.au", "theaustralian.com.au", "afr.com",
    "businessnewsdaily.com", "google.com", "bing.com",
    "unglobalcompact.org", "unglobalcompact.org.au",
}

def _is_valid_domain(url: str, company_name: str) -> Tuple[bool, float]:
    """Returns (is_valid, confidence)."""
    try:
        parsed = urlparse(url)
        ext = tldextract.extract(url)
        base = ext.domain.lower()
        if not base:
            return False, 0.0
        if ext.registered_domain.lower() in REJECT_DOMAINS:
            return False, 0.0
        # Check if company brand appears in domain
        brand_words = [w.lower() for w in re.split(r'\W+', company_name) if len(w) > 2]
        for w in brand_words:
            if w in base:
                return True, 0.9
        return True, 0.5
    except Exception:
        return False, 0.0


def discover_domain(
    company_name: str,
    participant_url: Optional[str],
    search: BaseSearchProvider,
) -> Tuple[Optional[str], Optional[str], float]:
    """
    Returns (website_url, domain, confidence).
    1. If participant_url looks like a company site, use it.
    2. Otherwise search.
    """
    # Check if participant URL is official
    if participant_url:
        valid, conf = _is_valid_domain(participant_url, company_name)
        if valid and conf >= 0.7:
            ext = tldextract.extract(participant_url)
            domain = ext.registered_domain
            if domain:
                logger.info(f"Domain from participant URL: {domain}")
                return participant_url, domain, conf

    # Search
    queries = [
        f'"{company_name}" official website Australia',
        f'"{company_name}" company website',
    ]
    for q in queries:
        try:
            results = search.search(q, num_results=5)
            for r in results:
                valid, conf = _is_valid_domain(r.url, company_name)
                if valid and conf >= 0.5:
                    ext = tldextract.extract(r.url)
                    domain = ext.registered_domain
                    if domain:
                        website = f"https://{domain}"
                        logger.info(f"Domain discovered via search: {domain} (conf={conf:.2f})")
                        return website, domain, conf
        except Exception as e:
            logger.warning(f"Domain search error for {company_name}: {e}")

    return None, None, 0.0
