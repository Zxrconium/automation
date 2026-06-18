"""Discover and apply email patterns from a company domain."""
import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("ungc.email_pattern")

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')

@dataclass
class PatternResult:
    pattern_name: str      # e.g. "first.last"
    pattern_template: str  # e.g. "{first}.{last}@domain.com"
    example: str
    source_url: str
    confidence: float

PATTERNS = [
    ("first.last",      lambda f, l: f"{f}.{l}"),
    ("firstlast",       lambda f, l: f"{f}{l}"),
    ("first_last",      lambda f, l: f"{f}_{l}"),
    ("flast",           lambda f, l: f"{f[0]}{l}"),
    ("f.last",          lambda f, l: f"{f[0]}.{l}"),
    ("last.first",      lambda f, l: f"{l}.{f}"),
    ("lastfirst",       lambda f, l: f"{l}{f}"),
    ("first",           lambda f, l: f"{f}"),
]

def extract_emails_from_text(text: str, domain: str) -> List[str]:
    """Extract emails from text that belong to the given domain."""
    emails = EMAIL_RE.findall(text)
    return [e.lower() for e in emails if e.lower().endswith(f"@{domain.lower()}")]


def infer_pattern(emails: List[str], domain: str) -> Optional[PatternResult]:
    """Given a list of emails from a domain, infer the naming pattern."""
    for email in emails:
        local = email.split("@")[0].lower()
        for pat_name, builder in PATTERNS:
            # Try to reverse-match: check if pattern can produce this local part
            # We need at least a plausible first/last. Try by splitting on separators.
            parts = re.split(r'[._\-]', local)
            if len(parts) >= 2:
                first, last = parts[0], parts[-1]
                if len(first) >= 2 and len(last) >= 2:
                    candidate = builder(first, last)
                    if candidate == local:
                        template = builder("{first}", "{last}") + f"@{domain}"
                        return PatternResult(
                            pattern_name=pat_name,
                            pattern_template=template,
                            example=email,
                            source_url="",
                            confidence=0.8,
                        )
    return None


def build_potential_email(
    first_name: str,
    last_name: str,
    domain: str,
    pattern: PatternResult,
) -> Optional[str]:
    """Apply discovered pattern to build a potential email."""
    if not first_name or not last_name:
        return None
    f = first_name.lower().strip()
    l = last_name.lower().strip()
    # Remove non-alpha
    f = re.sub(r'[^a-z]', '', f)
    l = re.sub(r'[^a-z]', '', l)
    if not f or not l:
        return None
    for pat_name, builder in PATTERNS:
        if pat_name == pattern.pattern_name:
            local = builder(f, l)
            return f"{local}@{domain}".lower()
    return None
