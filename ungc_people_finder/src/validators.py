"""Email and URL validation."""
import re
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse, urlencode
from urllib.parse import parse_qs

import dns.resolver
import dns.exception

logger = logging.getLogger("ungc.validators")

EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')

def is_valid_email_syntax(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def check_mx(domain: str) -> Tuple[bool, str]:
    """Check if domain has MX records. Returns (valid, reason)."""
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=5)
        if answers:
            return True, f"{len(answers)} MX record(s) found"
        return False, "No MX records"
    except dns.resolver.NXDOMAIN:
        return False, "Domain does not exist"
    except dns.resolver.NoAnswer:
        # Try A record as fallback
        try:
            dns.resolver.resolve(domain, 'A', lifetime=5)
            return True, "No MX but A record exists"
        except Exception:
            return False, "No MX or A record"
    except dns.exception.Timeout:
        return False, "DNS timeout"
    except Exception as e:
        return False, str(e)


def normalize_url(url: str) -> str:
    """Remove tracking params, normalize to clean URL."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        # Remove common tracking params
        tracking = {'utm_source','utm_medium','utm_campaign','utm_term','utm_content',
                    'fbclid','gclid','ref','source','_ga','mc_cid','mc_eid'}
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in tracking}
        from urllib.parse import urlencode
        new_query = urlencode({k: v[0] for k, v in clean_qs.items()})
        cleaned = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                               parsed.params, new_query, ''))
        return cleaned.rstrip('?&')
    except Exception:
        return url


def normalize_linkedin_url(url: str) -> Optional[str]:
    """Normalize LinkedIn profile URL."""
    if not url:
        return None
    url = normalize_url(url)
    # Ensure it's a linkedin.com/in/ URL
    parsed = urlparse(url)
    if 'linkedin.com' not in parsed.netloc:
        return None
    path = parsed.path.rstrip('/')
    if '/in/' not in path:
        return None
    # Keep only up to /in/username
    parts = path.split('/')
    try:
        in_idx = parts.index('in')
        clean_path = '/'.join(parts[:in_idx+2])
        return f"https://www.linkedin.com{clean_path}"
    except (ValueError, IndexError):
        return None
