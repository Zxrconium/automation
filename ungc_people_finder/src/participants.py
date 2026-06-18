"""Parse UNGC Australia participant page."""
import logging
import re
import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import Participant
from src import cache as cache_module

logger = logging.getLogger("ungc.participants")

DEFAULT_URL = "https://unglobalcompact.org.au/our-participants/"

class FetchBlockedError(Exception):
    """Raised when the remote server returns 403 or similar access-denied response."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8))
def _fetch(url: str) -> str:
    cached = cache_module.get(f"page:{url}", settings.cache_ttl_hours)
    if cached:
        return cached
    time.sleep(settings.request_delay)
    headers = {"User-Agent": settings.user_agent}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(url, headers=headers)
        if r.status_code == 403:
            raise FetchBlockedError(
                f"HTTP 403 Forbidden from {url}. "
                "The website blocked automated fetching. "
                "Open the page in a browser, save it as HTML, "
                "then rerun with --html-file."
            )
        r.raise_for_status()
    cache_module.set(f"page:{url}", r.text)
    return r.text


def _html_from_file(html_file: str) -> str:
    path = Path(html_file)
    if not path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")
    logger.info(f"Reading participants from local file: {html_file}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_participants(
    url: str = DEFAULT_URL,
    category_filter: Optional[str] = None,
    html_file: Optional[str] = None,
) -> List[Participant]:
    """
    Parse the UNGC AU participants page.
    Pass html_file to read from a locally saved HTML file instead of fetching the URL.
    The page uses headings (h2/h3/h4) to separate categories, followed by lists of companies.
    """
    base_url = url  # used for resolving relative hrefs
    if html_file:
        html = _html_from_file(html_file)
    else:
        logger.info(f"Fetching participants from {url}")
        html = _fetch(url)

    soup = BeautifulSoup(html, "lxml")

    participants: List[Participant] = []
    current_category = "Unknown"

    # Try to find the main content area
    main = soup.find("main") or soup.find("div", class_=re.compile(r"content|main|entry")) or soup.body

    # Walk all elements looking for headings and lists
    elements = main.find_all(["h1", "h2", "h3", "h4", "h5", "ul", "ol", "p", "div"])

    heading_tags = {"h1", "h2", "h3", "h4", "h5"}

    for el in elements:
        tag = el.name
        if tag in heading_tags:
            text = el.get_text(strip=True)
            if text:
                current_category = text
            continue

        if tag in ("ul", "ol"):
            for li in el.find_all("li", recursive=False):
                a = li.find("a")
                name = li.get_text(strip=True)
                link = None
                if a:
                    name = a.get_text(strip=True)
                    href = a.get("href", "")
                    if href and not href.startswith("#"):
                        link = urljoin(base_url, href)
                if not name:
                    continue
                cat = current_category
                if category_filter and category_filter.lower() not in cat.lower():
                    continue
                participants.append(Participant(
                    company_name=name,
                    source_category=cat,
                    participant_source_url=link,
                ))

    # Deduplicate by company name (case-insensitive)
    seen = set()
    unique = []
    for p in participants:
        key = p.company_name.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    logger.info(f"Found {len(unique)} participants (category_filter={category_filter!r})")
    return unique


def save_participants_csv(participants: List[Participant], path: str) -> None:
    import pandas as pd
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rows = [p.model_dump() for p in participants]
    pd.DataFrame(rows).to_csv(path, index=False)
    logger.info(f"Saved {len(participants)} participants to {path}")
