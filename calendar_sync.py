"""
Google Calendar Synchronization Module.

Every action gets a 2-week notice before it's due.
Each calendar event includes: simple action, timeline, funding amount, requirements.
"""
from __future__ import annotations
import logging
import json
import os
from datetime import datetime, timedelta
from typing import List

from models import Grant, ComplianceMatrix
from config import (
    CALENDAR_SCOPES, CALENDAR_CREDENTIALS_PATH,
    CALENDAR_TOKEN_PATH, CALENDAR_ID, OUTPUT_DIR,
    APPLICATION_READY_DATE, _parse_date, _central_tz, _effective_deadline,
)

logger = logging.getLogger("grantbot.calendar")

_gapi_available = False
_calendar_service = None


# ── Shared action definitions ────────────────────────────────────────────
# Both Google Calendar and ICS paths consume these. Single source of truth
# for timing, titles, descriptions, colors, and reminder offsets.

def _build_requirements(grant: Grant) -> list[str]:
    reqs = [
        "SAM.gov registration active",
        "UEI verified",
        "501(c)(3) or C-Corp proof",
        "Financial statements (most recent FY)",
        "Project narrative",
        "Budget + justification",
    ]
    if "rural" in grant.description.lower():
        reqs.append("Rural impact statement")
    return reqs


def _iter_actions(grant: Grant, deadline: datetime, now: datetime):
    """Yield action dicts for each milestone. Shared by GCal and ICS paths."""
    deadline_str = _effective_deadline(grant)
    reqs = _build_requirements(grant)
    name = grant.name[:50]
    common_reminders = [
        {"method": "popup", "minutes": 14 * 24 * 60},
        {"method": "email", "minutes": 14 * 24 * 60},
    ]

    # ACTION 0: Pre-registration (45 days before)
    if grant.pre_registration_required:
        due = deadline - timedelta(days=45)
        if due > now:
            yield {
                "uid_suffix": "a0",
                "summary": f"PRE-REGISTER: {name}",
                "start_hour": 9, "end_hour": 10,
                "colorId": "5",
                "action_text": (
                    "COMPLETE PRE-REGISTRATION for this program.\n"
                    "Create the account and finish any required courses/forms so "
                    "you are eligible when the application window opens."
                ),
                "requirements": ["Account created", "Required courses/forms completed"],
                "reminders": common_reminders,
                "due": due,
            }

    # ACTION 1: Edit & approve draft (30 days before)
    due = deadline - timedelta(days=30)
    if due > now:
        yield {
            "uid_suffix": "a1",
            "summary": f"EDIT & APPROVE DRAFT: {name}",
            "start_hour": 10, "end_hour": 11,
            "colorId": "2",
            "action_text": (
                "Review this opportunity and Edit & approve the draft application.\n"
                "Read the draft in output/drafts/, make any changes, then approve it."
            ),
            "requirements": reqs,
            "reminders": common_reminders,
            "due": due,
        }

    # ACTION 2: Submit attachments (16 days before)
    due = deadline - timedelta(days=16)
    if due > now:
        yield {
            "uid_suffix": "a2",
            "summary": f"SUBMIT ATTACHMENTS: {name}",
            "start_hour": 10, "end_hour": 11,
            "colorId": "6",
            "action_text": (
                "Gather required attachments and Submit any pre-registration forms.\n"
                "Check the compliance checklist in the draft file and upload documents."
            ),
            "requirements": [
                "SF-424 (Application for Federal Assistance)",
                "Organizational chart",
                "Resumes/CVs of key personnel",
                "Proof of entity status",
            ],
            "reminders": common_reminders,
            "due": due,
        }

    # ACTION 3: Click submit (3 days before)
    due = deadline - timedelta(days=3)
    if due > now:
        yield {
            "uid_suffix": "a3",
            "summary": f"SUBMIT APPLICATION: {name}",
            "start_hour": 14, "end_hour": 15,
            "colorId": "11",
            "action_text": (
                "Final review and Click submit on the application portal.\n"
                "Verify all documents are uploaded, then submit before midnight."
            ),
            "requirements": [
                "All attachments uploaded",
                "Application form complete",
                "Budget finalized",
            ],
            "reminders": common_reminders + [{"method": "popup", "minutes": 3 * 24 * 60}],
            "due": due,
        }


def _init_calendar_service():
    """Initialize Google Calendar API service."""
    global _gapi_available, _calendar_service
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(CALENDAR_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(CALENDAR_TOKEN_PATH, CALENDAR_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    logger.warning("Calendar token refresh failed")
                    _gapi_available = False
                    return
            else:
                if not os.path.exists(CALENDAR_CREDENTIALS_PATH):
                    logger.info("No calendar credentials — using ICS fallback")
                    _gapi_available = False
                    return
                flow = InstalledAppFlow.from_client_secrets_file(
                    CALENDAR_CREDENTIALS_PATH, CALENDAR_SCOPES
                )
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(CALENDAR_TOKEN_PATH), exist_ok=True)
            with open(CALENDAR_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        _calendar_service = build("calendar", "v3", credentials=creds)
        _gapi_available = True
        logger.info("Google Calendar API initialized")
    except ImportError:
        logger.info("Google API libraries not installed — using ICS fallback")
        _gapi_available = False
    except Exception as e:
        logger.warning(f"Calendar init failed: {e}")
        _gapi_available = False


def _build_action_description(grant: Grant, action: str, deadline_str: str,
                               requirements: List[str]) -> str:
    """Build a clean event description with timeline, funding, and requirements."""
    reqs = "\n".join(f"  - {r}" for r in requirements) if requirements else "  - None listed"

    return (
        f"WHAT TO DO\n"
        f"{action}\n\n"
        f"GRANT INFO\n"
        f"  Funder: {grant.funder}\n"
        f"  Funding: {grant.estimated_value}\n"
        f"  Deadline: {deadline_str}\n"
        f"  Score: {grant.match_score}/100\n\n"
        f"REQUIREMENTS\n"
        f"{reqs}\n\n"
        f"LINKS\n"
        f"  Source: {grant.source_url}\n"
        f"  Draft: output/drafts/ (see matching file)\n"
    )


def _schedule_single_grant(grant: Grant):
    """Create Google Calendar action events for a grant with a hard deadline."""
    deadline_str = _effective_deadline(grant)
    if not deadline_str or deadline_str == "Rolling":
        grant.calendar_status = "No fixed deadline"
        return

    try:
        deadline = _parse_date(deadline_str)
    except (ValueError, TypeError):
        grant.calendar_status = "Invalid deadline format"
        return

    if deadline is None:
        grant.calendar_status = "Invalid deadline format"
        return

    now = datetime.now(deadline.tzinfo)
    events_scheduled = 0

    for action in _iter_actions(grant, deadline, now):
        desc = _build_action_description(
            grant, action["action_text"], deadline_str, action["requirements"],
        )
        _insert_event({
            "summary": action["summary"],
            "description": desc,
            "start": {"dateTime": action["due"].replace(hour=action["start_hour"]).isoformat(), "timeZone": "America/Chicago"},
            "end": {"dateTime": action["due"].replace(hour=action["end_hour"]).isoformat(), "timeZone": "America/Chicago"},
            "colorId": action["colorId"],
            "reminders": {"useDefault": False, "overrides": action["reminders"]},
        })
        events_scheduled += 1

    grant.calendar_status = f"Scheduled ({events_scheduled} actions, 2-wk notice each)"
    grant.calendar_event_id = f"actions-{events_scheduled}"


def schedule_grant_events(grants: List[Grant]) -> List[Grant]:
    """Schedule action events for each grant with a deadline."""
    global _gapi_available
    if _calendar_service is None:
        _init_calendar_service()

    if not _gapi_available:
        for grant in grants:
            if grant.deadline and grant.deadline != "Rolling":
                grant.calendar_status = "Calendar API unavailable — ICS generated"
            else:
                grant.calendar_status = "No deadline to schedule"
        _generate_ics_fallback(grants)
        return grants

    for grant in grants:
        try:
            _schedule_single_grant(grant)
        except Exception as e:
            grant.calendar_status = f"Schedule error: {str(e)[:50]}"
            logger.warning(f"Failed to schedule {grant.name}: {e}")

    return grants


def _insert_event(event_body: dict) -> str | None:
    """Insert a single event into Google Calendar."""
    try:
        result = _calendar_service.events().insert(
            calendarId=CALENDAR_ID, body=event_body
        ).execute()
        return result.get("id")
    except Exception as e:
        logger.warning(f"Calendar insert failed: {e}")
        return None


def _ics_event_lines(action: dict, grant: Grant, uid_base: str, deadline_str: str) -> list[str]:
    """Build ICS event lines from a shared action dict."""
    due = action["due"]
    alarm_lines = []
    for r in action["reminders"]:
        trigger = r["minutes"]
        if trigger >= 14 * 24 * 60:
            trigger_str = "-P14D"
        elif trigger >= 3 * 24 * 60:
            trigger_str = "-P3D"
        else:
            trigger_str = f"-PT{trigger}M"
        alarm_lines.extend([
            "BEGIN:VALARM",
            f"TRIGGER:{trigger_str}",
            f"ACTION:{r['method'].upper()}",
            f"DESCRIPTION:{trigger_str} until {action['summary']}",
            "END:VALARM",
        ])

    req_str = " | ".join(action["requirements"])
    desc_text = action["action_text"].replace("\n", "\\n")
    return [
        "BEGIN:VEVENT",
        f"UID:{uid_base}-{action['uid_suffix']}@grantbot",
        f"DTSTART:{due.strftime('%Y%m%dT')}{action['start_hour']:02d}0000",
        f"DTEND:{due.strftime('%Y%m%dT')}{action['end_hour']:02d}0000",
        f"SUMMARY:{action['summary']}",
        f"DESCRIPTION:{desc_text}\\n"
        f"Funder: {grant.funder}\\nFunding: {grant.estimated_value}\\n"
        f"Deadline: {deadline_str}\\n"
        f"Requirements: {req_str}",
        *alarm_lines,
        "END:VEVENT",
    ]


def _generate_ics_fallback(grants: List[Grant]):
    """Generate .ics file with 2-week notice reminders for each action."""
    ics_path = OUTPUT_DIR / "grant_deadlines.ics"
    _tz = _central_tz()
    now = datetime.now(_tz)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GrantBot//Pipeline//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for grant in grants:
        deadline_str = _effective_deadline(grant)
        if not deadline_str or deadline_str == "Rolling":
            continue
        try:
            deadline = _parse_date(deadline_str)
        except (ValueError, TypeError):
            continue
        if deadline is None:
            continue

        uid_base = grant.id[:12]
        for action in _iter_actions(grant, deadline, now):
            lines.extend(_ics_event_lines(action, grant, uid_base, deadline_str))

    lines.append("END:VCALENDAR")

    ics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ics_path, "w") as f:
        f.write("\r\n".join(lines))
    logger.info(f"ICS saved: {ics_path}")
