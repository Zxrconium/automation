from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

class StatusEnum(str, Enum):
    complete_confirmed_email = "complete_confirmed_email"
    complete_potential_email = "complete_potential_email"
    person_found_no_email = "person_found_no_email"
    company_found_no_person = "company_found_no_person"
    domain_not_found = "domain_not_found"
    needs_manual_review = "needs_manual_review"
    error = "error"

class LinkedInConfidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class Participant(BaseModel):
    company_name: str
    source_category: str = ""
    participant_source_url: Optional[str] = None

class EmailPattern(BaseModel):
    pattern: str           # e.g. "first.last"
    example: str           # e.g. "jane.smith@company.com"
    source_url: str
    confidence: float = 0.0

class ResearchResult(BaseModel):
    source_category: str = ""
    company_name: str
    participant_source_url: Optional[str] = None
    company_website: Optional[str] = None
    company_domain: Optional[str] = None
    target_person_name: Optional[str] = None
    target_person_title: Optional[str] = None
    role_match_type: Optional[str] = None
    role_match_score: int = 0
    linkedin_profile_url: Optional[str] = None
    linkedin_confidence: Optional[str] = None
    linkedin_source_url: Optional[str] = None
    confirmed_email: Optional[str] = None
    confirmed_email_source_url: Optional[str] = None
    email_pattern_found: Optional[str] = None
    email_pattern_evidence: Optional[str] = None
    potential_email: Optional[str] = None
    potential_email_confidence: Optional[str] = None
    mx_valid: Optional[bool] = None
    other_public_emails_found: Optional[str] = None
    research_sources: Optional[str] = None
    confidence_score: int = 0
    status: str = StatusEnum.needs_manual_review
    notes: Optional[str] = None
    last_checked: Optional[str] = None
