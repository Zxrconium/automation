# UNGC People Finder

A research pipeline that finds HR/People executives at UN Global Compact Network Australia participant companies. It discovers company domains, identifies key People & Culture leaders, finds LinkedIn profiles, and surfaces confirmed or potential email addresses.

---

## Overview

The pipeline works in two stages:

1. **collect-participants** — scrapes the UNGC AU website to build a list of participant companies
2. **enrich** — for each company, it:
   - Discovers the official company domain
   - Searches for People/HR executives by title
   - Finds LinkedIn profiles via search APIs
   - Searches for confirmed email addresses on the domain
   - Infers email naming patterns and builds potential emails
   - Scores each result and exports to Excel + CSV

---

## Installation

```bash
cd ungc_people_finder
pip install -r requirements.txt
```

To install the `ungc` CLI command:

```bash
pip install -e .
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the relevant values:

```bash
cp .env.example .env
```

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_PROVIDER` | `mock` | Search backend: `mock`, `bing`, `serpapi`, `google` |
| `REQUEST_DELAY` | `1.5` | Seconds between page fetches |
| `SEARCH_DELAY` | `2.0` | Seconds between search API calls |
| `CACHE_TTL_HOURS` | `24` | How long to cache responses |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Search API Configuration

The tool supports four search backends. Set `SEARCH_PROVIDER` in `.env`:

### mock (default)
Returns no results. Safe for testing pipeline structure without spending API quota.

### Bing Web Search
```
SEARCH_PROVIDER=bing
BING_API_KEY=your_key_here
```
Get a key from [Azure Cognitive Services](https://azure.microsoft.com/en-au/products/ai-services/bing-search).

### SerpAPI
```
SEARCH_PROVIDER=serpapi
SERPAPI_KEY=your_key_here
```
Sign up at [serpapi.com](https://serpapi.com). Proxies Google results.

### Google Custom Search Engine
```
SEARCH_PROVIDER=google
GOOGLE_API_KEY=your_key_here
GOOGLE_CSE_ID=your_cse_id_here
```
Create a CSE at [programmablesearchengine.google.com](https://programmablesearchengine.google.com).

---

## CLI Usage

### Step 1: Collect participants

```bash
# All participants
python -m src.cli collect-participants --output data/output/participants.csv

# Filter to a specific category
python -m src.cli collect-participants --category "Business" --output data/output/business.csv
```

#### If the site blocks automated fetching (HTTP 403)

Some websites return 403 Forbidden to automated requests. In that case:

1. Open the participants page in your browser:
   `https://unglobalcompact.org.au/our-participants/`
2. Save the page as HTML: **File → Save As → Webpage, HTML Only**
3. Place the file at `data/input/ungc_participants.html`
4. Rerun with `--html-file`:

```bash
python -m src.cli collect-participants \
  --html-file data/input/ungc_participants.html \
  --category Business \
  --output data/output/participants.csv
```

The tool will print a clear message with these instructions if a 403 is encountered.

### Step 2: Enrich with People executive data

```bash
# All companies in the input file
python -m src.cli enrich --input data/output/participants.csv --output data/output/results.xlsx

# Limit to first 10 for testing
python -m src.cli enrich --input data/output/participants.csv --limit 10

# Single company
python -m src.cli enrich --input data/output/participants.csv --company "BHP"
```

### Clear cache

```bash
python -m src.cli clear-cache
```

If installed as CLI:

```bash
ungc collect-participants
ungc enrich --input data/output/participants.csv
ungc clear-cache
```

---

## How Confidence Scoring Works

Each result gets a 0–100 confidence score based on:

| Component | Max Points | Notes |
|-----------|-----------|-------|
| Domain discovery | 20 | Higher if brand name appears in domain |
| Role match score | 35 | Scaled from the role's target score (0–100) |
| LinkedIn found | 20 | high=20, medium=13, low=7 |
| Email found | 15 | Confirmed=15, potential=8 |
| Source count | 10 | 2 pts per source URL, capped at 10 |

**Score bands:**
- 80–100: High confidence, ready to use
- 50–79: Medium confidence, worth reviewing
- 20–49: Low confidence, manual review needed
- 0–19: Minimal signal found

---

## Confirmed vs Potential Emails

**Confirmed email** (`confirmed_email`): The person's email address was found verbatim in a public web page or search snippet — on the company's own domain and containing part of the person's name.

**Potential email** (`potential_email`): No direct email was found, but the tool inferred the company's email naming convention from other publicly visible emails on the same domain, then applied that pattern to the target person's name.

Example:
- Other public emails: `jane.smith@acme.com`, `bob.jones@acme.com`
- Pattern inferred: `{first}.{last}@acme.com`
- Potential email for "Sarah Brown": `sarah.brown@acme.com`

Potential emails are labeled with a confidence of `medium` (when a pattern was found) or `low`.

---

## Output Columns

The Excel output contains five sheets:

1. **Results** — full dataset with all columns, filterable
2. **Summary** — counts by status, averages
3. **Needs Manual Review** — subset where no person/email was found
4. **Email Pattern Evidence** — companies where an email pattern was inferred
5. **Sources Log** — all URLs used during research

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- Email pattern extraction and inference (`test_email_patterns.py`)
- Role title matching and scoring (`test_role_matching.py`, `test_scoring.py`)
- Participant page parsing (`test_participant_parser.py`)
- URL and email validation (`test_validators.py`)

---

## Legal and Ethical Constraints

- This tool only retrieves **publicly available** information from company websites and search engine results.
- It does **not** scrape LinkedIn profiles directly. LinkedIn URLs are discovered via search engine results only.
- Email addresses returned are only those already **visible in public web content**.
- Potential emails are **inferences** — they may belong to a real person or may not exist. Do not send unsolicited email without verifying consent and compliance with Australian Spam Act 2003 and GDPR if applicable.
- Use responsibly. Respect `robots.txt` and rate limits.
- The `REQUEST_DELAY` and `SEARCH_DELAY` settings are enforced to avoid hammering servers.
