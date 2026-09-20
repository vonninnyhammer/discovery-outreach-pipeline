"""
Configuration for the Opportunity Discovery & Outreach pipeline.

Rename this file to `config.py` and fill in your own values. Nothing here is
secret — but it is entirely personal, which is why it ships as an example.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DRAFTS_DIR = OUTPUT_DIR / "drafts"
GRANTS_DB_FILE = OUTPUT_DIR / "grants_db.json"
DASHBOARD_FILE = OUTPUT_DIR / "grant_dashboard.md"

# ── VENTURE PROFILE (used to fill application drafts) ──────────────────────
VENTURE_NAME = "Example Venture"
VENTURE_DESCRIPTION = "a technology access and workforce skills program"
VENTURE_MISSION = "affordable technology access and modern workforce skills"

# For-profit entity operating the pipeline. Set HOLD_MODE True until the
# entity is fully registered and application-ready.
FOR_PROFIT_ENTITY = "Example Venture LLC"

# Geographic service area (fill with your own)
CITY = "Example City"
STATE = "Example State"
COUNTY = "Example County"
ZIP_CODE = "00000"
CENTRAL_TZ = ZoneInfo("America/Chicago")
def _central_tz():
    return CENTRAL_TZ

# ── Application readiness gate ──────────────────────────────────────────────
# Before this date the pipeline only prepares drafts; it never submits.
APPLICATION_READY_DATE = "2027-01-01"
# HOLD_MODE: when True, the dashboard prints a hold banner and nothing is
# treated as actionable. Flip to False once the entity is ready.
HOLD_MODE = True

# ── Discovery sources ───────────────────────────────────────────────────────
SOURCES = {
    "grants_gov": {"enabled": True, "api_key": ""},
    "web_search": {"enabled": True},
}

# ── Targeting ───────────────────────────────────────────────────────────────
TARGET_CATEGORIES = [
    "ai_tech_innovation",
    "small_business",
    "rural_development",
    "workforce_training",
    "digital_inclusion",
    "youth_development",
    "reentry_rehabilitation",
]

SCORING_WEIGHTS = {
    "geographic_match": 20,
    "category_alignment": 25,
    "workforce_relevance": 20,
    "funding_amount": 10,
    "deadline_feasibility": 15,
    "rolling_or_micro": 10,
}

# For-profit-only gate. "both" is excluded (implies nonprofit paperwork).
ENTITY_TARGETS = {"for_profit"}

EXCLUSION_KEYWORDS = [
    "lottery", "payday loan", "religious", "political campaign",
    "membership fee required", "for a fee",
]

# ── Google Calendar ─────────────────────────────────────────────────────────
CALENDAR_ID = "primary"
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_CREDENTIALS_PATH = BASE_DIR / "credentials.json"
CALENDAR_TOKEN_PATH = BASE_DIR / "token.json"

# ── Date helpers (kept here so one module owns timezone behavior) ──────────
def _parse_date(value: str) -> datetime | None:
    """Parse an ISO date string into a Central-time-aware datetime.
    Date-only strings are interpreted in the local Central timezone."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(str(value), "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_central_tz())
    return dt


def _effective_deadline(grant) -> str | None:
    """Return the deadline that actually matters for scheduling.

    If the grant is not application-ready yet and a concrete next-cycle date is
    known, target the next cycle instead of the (already-past) current one.
    """
    if not getattr(grant, "application_ready", True) and grant.next_cycle_deadline:
        return grant.next_cycle_deadline
    return grant.deadline