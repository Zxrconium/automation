import pytest
from src.validators import is_valid_email_syntax, normalize_url, normalize_linkedin_url

def test_valid_email():
    assert is_valid_email_syntax("john.doe@company.com")
    assert is_valid_email_syntax("j.smith+tag@sub.domain.co.uk")

def test_invalid_email():
    assert not is_valid_email_syntax("notanemail")
    assert not is_valid_email_syntax("@domain.com")
    assert not is_valid_email_syntax("user@")

def test_normalize_url_removes_utm():
    url = "https://example.com/page?utm_source=google&utm_medium=cpc&id=123"
    result = normalize_url(url)
    assert "utm_source" not in result
    assert "id=123" in result

def test_normalize_linkedin():
    url = "https://www.linkedin.com/in/john-doe/?trk=something"
    result = normalize_linkedin_url(url)
    assert result == "https://www.linkedin.com/in/john-doe"

def test_normalize_linkedin_non_profile():
    url = "https://www.linkedin.com/company/acme"
    result = normalize_linkedin_url(url)
    assert result is None

def test_normalize_linkedin_none():
    assert normalize_linkedin_url("") is None
    assert normalize_linkedin_url(None) is None
