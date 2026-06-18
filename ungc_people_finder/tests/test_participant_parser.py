import pytest
import tempfile
import os
from unittest.mock import patch
from src.participants import parse_participants, FetchBlockedError
from src.models import Participant

SAMPLE_HTML = """
<html><body>
<main>
  <h2>Business</h2>
  <ul>
    <li><a href="https://bhp.com">BHP</a></li>
    <li><a href="https://anz.com">ANZ Bank</a></li>
  </ul>
  <h2>Academic Institutions</h2>
  <ul>
    <li>University of Sydney</li>
  </ul>
</main>
</body></html>
"""

def test_parse_all_categories():
    with patch("src.participants._fetch", return_value=SAMPLE_HTML):
        participants = parse_participants("https://example.com")
    names = [p.company_name for p in participants]
    assert "BHP" in names
    assert "ANZ Bank" in names
    assert "University of Sydney" in names

def test_filter_by_category():
    with patch("src.participants._fetch", return_value=SAMPLE_HTML):
        participants = parse_participants("https://example.com", category_filter="Business")
    names = [p.company_name for p in participants]
    assert "BHP" in names
    assert "ANZ Bank" in names
    assert "University of Sydney" not in names

def test_category_assigned():
    with patch("src.participants._fetch", return_value=SAMPLE_HTML):
        participants = parse_participants("https://example.com")
    bhp = next(p for p in participants if p.company_name == "BHP")
    assert bhp.source_category == "Business"
    uni = next(p for p in participants if p.company_name == "University of Sydney")
    assert uni.source_category == "Academic Institutions"

def test_participant_url_captured():
    with patch("src.participants._fetch", return_value=SAMPLE_HTML):
        participants = parse_participants("https://example.com")
    bhp = next(p for p in participants if p.company_name == "BHP")
    assert bhp.participant_source_url == "https://bhp.com"

def test_deduplication():
    html = """<html><body><main>
      <h2>Business</h2>
      <ul><li>ACME Corp</li><li>ACME Corp</li></ul>
    </main></body></html>"""
    with patch("src.participants._fetch", return_value=html):
        participants = parse_participants("https://example.com")
    assert len([p for p in participants if p.company_name == "ACME Corp"]) == 1


# --- html_file fallback tests ---

def test_parse_from_html_file():
    """parse_participants reads from a local file when html_file is given."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_HTML)
        tmp_path = f.name
    try:
        participants = parse_participants(html_file=tmp_path)
        names = [p.company_name for p in participants]
        assert "BHP" in names
        assert "ANZ Bank" in names
        assert "University of Sydney" in names
    finally:
        os.unlink(tmp_path)


def test_parse_from_html_file_with_category_filter():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_HTML)
        tmp_path = f.name
    try:
        participants = parse_participants(category_filter="Business", html_file=tmp_path)
        names = [p.company_name for p in participants]
        assert "BHP" in names
        assert "University of Sydney" not in names
    finally:
        os.unlink(tmp_path)


def test_html_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        parse_participants(html_file="/nonexistent/path/page.html")


def test_html_file_skips_fetch():
    """When html_file is provided, _fetch should never be called."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_HTML)
        tmp_path = f.name
    try:
        with patch("src.participants._fetch") as mock_fetch:
            parse_participants(html_file=tmp_path)
            mock_fetch.assert_not_called()
    finally:
        os.unlink(tmp_path)


def test_fetch_blocked_error_on_403():
    """_fetch raises FetchBlockedError on HTTP 403."""
    import httpx
    with patch("src.participants._fetch", side_effect=FetchBlockedError("HTTP 403 Forbidden")):
        with pytest.raises(FetchBlockedError, match="403"):
            parse_participants("https://example.com")
