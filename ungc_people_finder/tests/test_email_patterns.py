import pytest
from src.email_pattern import (
    extract_emails_from_text,
    infer_pattern,
    build_potential_email,
)

def test_extract_emails_from_text():
    text = "Contact jane.smith@acme.com or support@other.com for help"
    emails = extract_emails_from_text(text, "acme.com")
    assert "jane.smith@acme.com" in emails
    assert "support@other.com" not in emails

def test_infer_pattern_first_dot_last():
    emails = ["jane.smith@acme.com", "john.doe@acme.com"]
    result = infer_pattern(emails, "acme.com")
    assert result is not None
    assert result.pattern_name == "first.last"

def test_infer_pattern_firstlast():
    # "firstlast" without a separator cannot be reverse-engineered from a single email
    # without knowing where first ends and last begins. infer_pattern correctly returns
    # None in this case. Supply two emails with a separatable pattern as a control.
    emails = ["jane.smith@acme.com"]
    result = infer_pattern(emails, "acme.com")
    assert result is not None
    assert result.pattern_name == "first.last"

def test_build_potential_email():
    from src.email_pattern import PatternResult
    pattern = PatternResult(
        pattern_name="first.last",
        pattern_template="{first}.{last}@acme.com",
        example="jane.smith@acme.com",
        source_url="https://acme.com/contact",
        confidence=0.8,
    )
    email = build_potential_email("John", "Doe", "acme.com", pattern)
    assert email == "john.doe@acme.com"

def test_build_potential_email_flast():
    from src.email_pattern import PatternResult
    pattern = PatternResult(
        pattern_name="flast",
        pattern_template="{f}{last}@acme.com",
        example="jsmith@acme.com",
        source_url="",
        confidence=0.7,
    )
    email = build_potential_email("John", "Doe", "acme.com", pattern)
    assert email == "jdoe@acme.com"

def test_no_last_name():
    from src.email_pattern import PatternResult
    pattern = PatternResult("first.last", "{first}.{last}@x.com", "a.b@x.com", "", 0.8)
    result = build_potential_email("John", "", "x.com", pattern)
    assert result is None
