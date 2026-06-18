import pytest
from unittest.mock import patch
from src.participants import parse_participants
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
