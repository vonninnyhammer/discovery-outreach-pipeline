# Opportunity Discovery & Outreach Pipeline

A fully local, single-machine pipeline that discovers grant and funding
opportunities, scores them against your venture profile, generates application
drafts, writes calendar reminders, and renders a Markdown dashboard.

The pipeline is **governed by config, not by code**: fill in `config.example.py`
(renamed to `config.py`) with your own profile and the same codebase works for
any program area or region. No third-party cloud is involved — discovery hits
public APIs and search engines directly, and everything else runs locally.

## What it does

| Stage | Module | Output |
|-------|--------|--------|
| Discover | `discover/` | Scrapes Grants.gov API, web search fallback, OpenGrants |
| Curate | `curated.py` | Known-good researched targets merged into the pipeline |
| Filter & Score | `filter.py` | Geographic, category, workforce, funding, deadline scores (0-100) |
| Draft | `draft.py` | Compliance matrix + pre-written application draft per grant |
| Calendar | `calendar_sync.py` | 4 milestone events per grant (45d pre-reg, 30d/16d/3d) via Google Calendar or ICS fallback |
| Dashboard | `dashboard.py` | Single Markdown view of the whole pipeline + local resource registry |

## Quick start

```bash
pip install -r requirements.txt

# 1. Configure
cp config.example.py config.py   # then edit to your profile

# 2. Run (offline uses the curated registry + existing DB, no network)
python pipeline.py --offline

# 3. Run the full live cycle (network discovery + curated merge)
python pipeline.py
```

Outputs land in `output/`:
- `output/grant_dashboard.md` — the pipeline summary
- `output/drafts/*.md` — per-grant compliance matrices and application drafts
- `output/grants_db.json` — the deduplicated grant database
- `output/grant_deadlines.ics` — ICS calendar fallback (no Google API needed)

### Headline value vs. realistic cash

A grant's `estimated_value` is whatever the funder advertises — often a pool size
or a maximum award — so those figures are never added up. Each curated entry can
also carry `realistic_award_usd`, a defensible award for this applicant, and an
`award_blocked_reason` when that is $0 (loan rather than grant, nonprofit-only,
revenue minimum, and so on). The dashboard sums only the realistic figures, and
lists entries without one as "not assessed".

Geography is reported as verified only when an affirmative signal is found
(federal program, your state named, rural focus). A grant that merely lacks a
disqualifying keyword still passes, but is marked "unver." and scores half the
geographic points.

## Scheduling

`cron_run.sh` shows a cron line for a nightly `--offline` run.

Google Calendar is optional. With `credentials.json` present it pushes events;
without it, the pipeline emits `output/grant_deadlines.ics` instead.

## Safety model

- `HOLD_MODE = True` (default): the pipeline only prepares drafts. Nothing is
  submitted anywhere.
- `APPLICATION_READY_DATE`: grants whose cycle closes before this date are
  re-targeted to their next cycle instead of being treated as actionable.
- For-profit-only gate: grants requiring a nonprofit entity are excluded.
- Hard-exclusion keyword list in `config.py` drops programs that are lotteries,
  fee-based, or otherwise outside scope.

## Structure

```
discover/            discovery sources (Grants.gov, web fallback, OpenGrants)
models.py            Grant / ComplianceMatrix / ApplicationDraft dataclasses
filter.py            scoring + exclusion engine
draft.py             application draft generator
calendar_sync.py     Google Calendar + ICS milestone events
dashboard.py         Markdown dashboard renderer
curated.py           manually researched, verified targets
local_regional.py    local/regional assistance registry (uses YOUR area's data)
pipeline.py          orchestrator: Discover → Filter → Draft → Calendar → Dashboard
config.example.py    profile to copy to config.py
```

## Notes

- The curated registry (`curated.py`) ships with representative programs as
  examples. Replace or prune them for your area — they are researched, not scraped.
- `local_regional.py` contains neutral example entries; replace them with the
  real loans, tax incentives, and free assistance available where you operate.