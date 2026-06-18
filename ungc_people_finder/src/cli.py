"""CLI entry point."""
import logging
import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
import pandas as pd

from src.logging_config import setup_logging
from src.config import settings
from src.models import ResearchResult, StatusEnum
from src.participants import parse_participants, save_participants_csv
from src.search import get_provider
from src.company_domain import discover_domain
from src.people_research import research_people
from src.linkedin_finder import find_linkedin
from src.email_finder import find_emails, build_potential
from src.validators import check_mx, normalize_url
from src.scoring import compute_confidence
from src.exporters import export

setup_logging()
logger = logging.getLogger("ungc.cli")
app = typer.Typer(help="UNGC People Finder - Research HR executives at UNGC AU participants")

UNGC_URL = "https://unglobalcompact.org.au/our-participants/"


@app.command("collect-participants")
def collect_participants(
    url: str = typer.Option(UNGC_URL, help="UNGC participants page URL"),
    category: Optional[str] = typer.Option(None, help="Filter by category, e.g. 'Business'"),
    output: str = typer.Option("data/output/participants.csv", help="Output CSV path"),
):
    """Collect participant companies from the UNGC AU website."""
    participants = parse_participants(url, category_filter=category)
    save_participants_csv(participants, output)
    typer.echo(f"Collected {len(participants)} participants → {output}")


def _enrich_company(company_name: str, source_category: str, participant_url: Optional[str], search) -> ResearchResult:
    logger.info(f"Processing: {company_name}")
    now = datetime.utcnow().isoformat()
    result = ResearchResult(
        company_name=company_name,
        source_category=source_category,
        participant_source_url=participant_url,
        last_checked=now,
    )

    try:
        # 1. Domain
        website, domain, domain_conf = discover_domain(company_name, participant_url, search)
        result.company_website = website
        result.company_domain = domain

        if not domain:
            result.status = StatusEnum.domain_not_found
            result.notes = "Could not determine company domain"
            result.confidence_score = compute_confidence(0, 0, False, None, False, False, 0)
            return result

        # 2. MX check
        mx_valid, mx_reason = check_mx(domain)
        result.mx_valid = mx_valid
        logger.debug(f"MX {domain}: {mx_reason}")

        # 3. Find person
        person_name, person_title, role_score, role_match_type, sources = research_people(
            company_name, domain, search
        )
        result.target_person_name = person_name
        result.target_person_title = person_title
        result.role_match_score = role_score
        result.role_match_type = role_match_type
        result.research_sources = " | ".join(sources)

        if not person_name:
            result.status = StatusEnum.company_found_no_person
            result.confidence_score = compute_confidence(domain_conf, 0, False, None, False, False, len(sources))
            return result

        # 4. LinkedIn
        li_url, li_conf, li_source = find_linkedin(person_name, company_name, person_title or "", search)
        if li_url:
            result.linkedin_profile_url = li_url
            result.linkedin_confidence = li_conf
            result.linkedin_source_url = li_source

        # 5. Emails
        confirmed, confirmed_src, pattern, other_emails = find_emails(
            person_name, company_name, domain, search
        )
        result.confirmed_email = confirmed
        result.confirmed_email_source_url = confirmed_src

        if pattern:
            result.email_pattern_found = pattern.pattern_template
            result.email_pattern_evidence = f"{pattern.example} found via search"

        if other_emails:
            result.other_public_emails_found = " | ".join(other_emails)

        # 6. Potential email
        potential = build_potential(person_name, domain, pattern)
        if potential and potential != confirmed:
            result.potential_email = potential
            result.potential_email_confidence = "medium" if pattern else "low"

        # 7. Status
        if confirmed:
            result.status = StatusEnum.complete_confirmed_email
        elif potential:
            result.status = StatusEnum.complete_potential_email
        elif person_name:
            result.status = StatusEnum.person_found_no_email
        else:
            result.status = StatusEnum.company_found_no_person

        # 8. Confidence
        result.confidence_score = compute_confidence(
            domain_conf=domain_conf,
            role_score=role_score,
            has_linkedin=bool(li_url),
            linkedin_conf=li_conf if li_url else None,
            has_confirmed_email=bool(confirmed),
            has_potential_email=bool(potential),
            source_count=len(sources),
        )

    except Exception as e:
        logger.error(f"Error processing {company_name}: {e}", exc_info=True)
        result.status = StatusEnum.error
        result.notes = str(e)

    return result


@app.command("enrich")
def enrich(
    input: str = typer.Option(..., help="Input CSV of participants"),
    output: str = typer.Option("data/output/ungc_people_results.xlsx", help="Output Excel path"),
    limit: Optional[int] = typer.Option(None, help="Max companies to process"),
    company: Optional[str] = typer.Option(None, help="Process only this specific company name"),
):
    """Enrich participant companies with People executive contact data."""
    input_path = Path(input)
    if not input_path.exists():
        typer.echo(f"Input file not found: {input}", err=True)
        raise typer.Exit(1)

    df = pd.read_csv(input_path)
    search = get_provider()

    if company:
        df = df[df["company_name"].str.lower() == company.lower()]
        if df.empty:
            typer.echo(f"Company '{company}' not found in input", err=True)
            raise typer.Exit(1)

    if limit:
        df = df.head(limit)

    typer.echo(f"Enriching {len(df)} companies with {settings.search_provider} search provider...")

    results = []
    for _, row in df.iterrows():
        r = _enrich_company(
            company_name=str(row.get("company_name", "")),
            source_category=str(row.get("source_category", "")),
            participant_url=row.get("participant_source_url") if pd.notna(row.get("participant_source_url")) else None,
            search=search,
        )
        results.append(r)
        typer.echo(f"  [{r.status}] {r.company_name} — score={r.confidence_score}")

    export(results, output)
    typer.echo(f"\nDone. Results saved to {output} (and .csv)")


@app.command("clear-cache")
def clear_cache():
    """Clear the local request/search cache."""
    from src import cache as c
    count = c.clear()
    typer.echo(f"Cleared {count} cache entries")


def main():
    app()


if __name__ == "__main__":
    main()
