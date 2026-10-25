---
name: skill-module-authority-search
description: Stateless authority-tier search and retrieval module. Coordinates targeted query construction, official source whitelisting, exclusion filtering (blocking forums, blogs, unverified leaks), and candidate extraction across trend intelligence domains.
---
# Skill Module: Authority Search

Stateless retrieval and source-ranking module responsible for constructing domain-specific search recipes, executing hierarchical queries against official white-listed domains, and filtering out low-credibility sources.

## When to Use

Use this module whenever a trend report pipeline needs to gather factual updates from primary official authorities and designated tier-1 wire services (such as Reuters).

## Input Requirements

- `domain`: Intelligence domain (`geopolitics`, `visa`, `economy`, `na_politics`).
- `primary_domains`: List of authoritative domains (e.g. `canada.ca`, `uscis.gov`, `federalreserve.gov`, `whitehouse.gov`).
- `secondary_sources`: List of approved wire services (e.g. `reuters.com`).
- `target_entities`: List of nations, agencies, tickers, or legislative bodies to monitor.
- `time_window`: Focus time window (e.g. past 24 to 48 hours or past 14 days).
- `exclusion_patterns`: Forbidden source types (`forum`, `blog`, `consultant`, `unnamed_leaks`).

## Process

1. **Query Construction (Search Recipes)**:
   - For each entity in `target_entities`, construct scoped search queries combining entity name, action keywords, and site constraints (e.g., `site:<primary_domain> <entity> <keywords> <time_window>`).
   - Add secondary wire search: `<entity> <keywords> site:reuters.com <time_window>`.
2. **Execution & Deduplication**:
   - Issue search queries across target sectors.
   - Aggregate candidate URLs and snippets.
3. **Source Tier Filtering**:
   - Tier 1: Primary official releases, government gazettes, central bank communiques, statutory filings.
   - Tier 2: Reuters reporting citing official primary releases.
   - Discard: Any consultant blogs, social media threads, advocacy briefs, or anonymous leaks.
4. **Candidate Fact Extraction**:
   - Extract raw candidate occurrences with entity, timestamp, verified URL, and cited justification text.

## Output

Returns a structured candidate fact dataset:
- `candidates`: Array of verified items:
  - `entity`: Subject country, agency, or market instrument.
  - `action`: Specific policy, rate, rule, or deployment change.
  - `effective_date`: Date of announcement or enactment.
  - `official_url`: Verifiable primary source URL.
  - `stated_reason`: Officially stated rationale (or marked "官方未說明理由").
  - `tier`: `TIER_1_PRIMARY` or `TIER_2_REUTERS`.

## Validation Checklist

- [ ] All returned candidates originate strictly from `primary_domains` or approved `secondary_sources`.
- [ ] No consultant blogs, forums, or anonymous leak articles in the candidate list.
- [ ] Every candidate retains an active, verified URL.
