from src.scoring import match_role, compute_confidence

def test_all_target_roles_have_scores():
    from src.scoring import TARGET_ROLES
    for role, score in TARGET_ROLES:
        assert 0 < score <= 100, f"Bad score for {role}: {score}"

def test_match_role_executive_general_manager():
    _, score, _ = match_role("Executive General Manager People & Culture")
    assert score >= 85

def test_match_role_vp_people():
    _, score, _ = match_role("VP People")
    assert score >= 75

def test_confidence_no_email_no_linkedin():
    score = compute_confidence(0.8, 90, False, None, False, False, 3)
    assert 20 < score < 80

def test_confidence_max():
    score = compute_confidence(1.0, 100, True, "high", True, False, 10)
    assert score >= 80
