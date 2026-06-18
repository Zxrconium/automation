import pytest
from src.scoring import match_role, compute_confidence

def test_exact_cpo():
    role, score, mtype = match_role("Chief People Officer")
    assert score == 100
    assert mtype == "exact"

def test_exact_chro():
    role, score, mtype = match_role("Chief Human Resources Officer")
    assert score == 100

def test_fuzzy_head_of_people():
    role, score, mtype = match_role("Head of People & Culture")
    assert score >= 80
    assert mtype in ("exact", "fuzzy")

def test_hr_director():
    role, score, mtype = match_role("HR Director")
    assert score >= 75

def test_low_match():
    role, score, mtype = match_role("Marketing Manager")
    assert score < 50

def test_empty_title():
    role, score, mtype = match_role("")
    assert score == 0
    assert mtype == "none"

def test_compute_confidence_full():
    score = compute_confidence(
        domain_conf=0.9,
        role_score=100,
        has_linkedin=True,
        linkedin_conf="high",
        has_confirmed_email=True,
        has_potential_email=False,
        source_count=5,
    )
    assert score >= 70

def test_compute_confidence_minimal():
    score = compute_confidence(0, 0, False, None, False, False, 0)
    assert score == 0
