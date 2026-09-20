"""
Markdown Dashboard Output Formatter.

Generates a structured Markdown dashboard tracking:
[Grant Name, Funder, Estimated Value, Use-Type, Deadline, Match Score, Calendar Status]
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import List

from models import Grant
from config import DASHBOARD_FILE, OUTPUT_DIR, HOLD_MODE

logger = logging.getLogger("grantbot.dashboard")


def render_dashboard(grants: List[Grant], stats: dict = None) -> str:
    """Render a complete Markdown dashboard."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total_value = "N/A"
    if stats:
        total_value = stats.get("total_estimated_value", "N/A")

    if HOLD_MODE:
        hold_banner = (
            "> **HOLD MODE** — All outputs are drafts/preparation only. "
            "No applications submitted, no funds accepted, no capital disbursed. "
            "Set HOLD_MODE=false in config once the entity is application-ready."
        )
    else:
        hold_banner = "> Applications enable when `HOLD_MODE` is false in config."

    lines = [
        "# Grant Pipeline Dashboard",
        f"*Generated: {now}*",
        "",
        hold_banner,
        "",
        "---",
        "",
        "## Pipeline Summary",
        "",
        f"- **Total Discovered:** {stats.get('total_discovered', 'N/A') if stats else 'N/A'}",
        f"- **Qualified (after filtering):** {stats.get('qualified', len(grants)) if stats else len(grants)}",
        f"- **Excluded (safety filter):** {stats.get('excluded', 'N/A') if stats else 'N/A'}",
        f"- **Total Estimated Value:** {total_value}",
        f"- **Calendar Events Scheduled:** {stats.get('calendar_events', 'N/A') if stats else 'N/A'}",
        f"- **Drafts Generated:** {stats.get('drafts_generated', len(grants)) if stats else len(grants)}",
        "",
        "---",
        "",
        "## Active Grant Opportunities",
        "",
        "| # | Grant Name | Funder | Est. Value | Entity | Deadline | Ready | Next Cycle | Score |",
        "|---|-----------|--------|-----------|--------|----------|-------|------------|-------|",
    ]

    for i, g in enumerate(grants, 1):
        name = g.name[:45] + ("..." if len(g.name) > 45 else "")
        deadline_display = g.deadline if g.deadline else "Rolling/None"
        if deadline_display and len(deadline_display) > 12:
            deadline_display = deadline_display[:10]
        ready = "YES" if g.application_ready else "NO"
        next_cycle = (g.next_cycle_deadline or "—")
        if next_cycle and len(next_cycle) > 12:
            next_cycle = next_cycle[:10]
        lines.append(
            f"| {i} | [{name}]({g.source_url}) | {g.funder[:22]} "
            f"| {g.estimated_value[:14]} | {g.entity_target[:9]} "
            f"| {deadline_display} | {ready} | {next_cycle} | {g.match_score} |"
        )

    # ── Next Cycle Targets ────────────────────────────────
    # Only grants with a CONCRETE next-cycle date (auto-flagged "TBD" entries
    # from discovery are already visible in the main table via Ready=NO).
    next_cycle = [
        g for g in grants
        if g.next_cycle_deadline and not g.next_cycle_deadline.startswith("TBD")
    ]
    lines.extend([
        "",
        "---",
        "",
        "## Next Cycle Targets",
        "",
        "Grants tracked for their next open window. 'Ready' = current cycle is "
        "actionable now; 'NO' = current cycle closes before the ready date, so "
        "the next cycle is the target.",
        "",
        "| Grant Name | Entity | Ready | Next Cycle | Notes |",
        "|-----------|--------|-------|-----------|-------|",
    ])
    if next_cycle:
        for g in sorted(next_cycle, key=lambda x: x.next_cycle_deadline or "9999"):
            notes = "; ".join(g.notes[:2]) if g.notes else ""
            ready = "YES" if g.application_ready else "NO"
            lines.append(
                f"| {g.name[:45]} | {g.entity_target[:9]} | {ready} "
                f"| {g.next_cycle_deadline or 'TBD'} | {notes[:60]} |"
            )
    else:
        lines.append("| *(None — all grants actionable)* | | | | |")

    # ── Pre-Registration Programs ─────────────────────────
    pre_reg = [g for g in grants if g.pre_registration_required]
    lines.extend([
        "",
        "---",
        "",
        "## Pre-Registration Programs",
        "",
        "Programs requiring an account/coursework BEFORE the application window. "
        "Complete these early so you are eligible when the cycle opens.",
        "",
        "| Grant Name | Funder | Action Required |",
        "|-----------|--------|-----------------|",
    ])
    if pre_reg:
        for g in pre_reg:
            action = "; ".join(n for n in g.notes if "PRE-REGISTRATION" in n) or "Register early"
            lines.append(f"| {g.name[:45]} | {g.funder[:25]} | {action[:70]} |")
    else:
        lines.append("| *(None)* | | |")

    # ── Top 5 Opportunities ───────────────────────────────
    lines.extend([
        "",
        "---",
        "",
        "## Top 5 Opportunities (by Match Score)",
        "",
    ])

    for g in grants[:5]:
        lines.extend([
            f"### {g.name}",
            f"- **Funder:** {g.funder}",
            f"- **Value:** {g.estimated_value}",
            f"- **Category:** {g.category}",
            f"- **Entity Target:** {g.entity_target}",
            f"- **Score:** {g.match_score}/100",
            f"- **Deadline:** {g.deadline or 'Rolling'}",
            f"- **Next Cycle:** {g.next_cycle_deadline or '—'}",
            f"- **Application Ready:** {'YES' if g.application_ready else 'NO'}",
            f"- **Calendar:** {g.calendar_status}",
            f"- **Source:** [{g.source}]({g.source_url})",
            "",
            "**Quick Summary:**",
            f"> {g.description[:300]}{'...' if len(g.description) > 300 else ''}",
            "",
            "---",
            "",
        ])

    # Exclusion log
    lines.extend([
        "## Exclusion Log",
        "",
        "| Grant | Reason |",
        "|-------|--------|",
    ])
    # Note: excluded grants aren't in the qualified list, so we log this separately
    lines.append("| *(Excluded grants are logged in pipeline output)* | |")

    lines.extend([
        "",
        "---",
        "",
        "## Local & Regional Funding / Assistance",
        "",
        "**These are NOT grant lotteries.** They are loans, equity, tax incentives, "
        "and free assistance that scale with operating a real local business. "
        "Entries come from `local_regional.py` — replace them with your area's resources.",
        "",
        "| Resource | Type | Amount | Use By | Status |",
        "|----------|------|--------|--------|--------|",
    ])

    # Local/regional resources streamed in from the registry while staying
    # fully local — the pipeline never phones home.
    try:
        import importlib
        local_reg = importlib.import_module("local_regional")
        resources = local_reg.get_local_regional_resources()
        for r in resources:
            lines.append(
                f"| {r['name']} | {r['kind']} | {r['amount'][:32]} "
                f"| {r['use_by'][:44]} | {r['status']} |"
            )
    except Exception:
        lines.append("| *(No local resources registered)* | | | |")

    lines.extend([
        "",
        "---",
        "",
        "## Compliance Checklist",
        "",
        "**Entity Setup (for-profit only):**",
        "- [ ] For-profit entity (LLC/C-Corp) formed",
        "- [ ] SAM.gov registration active",
        "- [ ] UEI (Unique Entity Identifier) verified",
        "- [ ] UEI not on SAM.gov exclusions list",
        "",
        "**Federal Readiness:**",
        "- [ ] Grants.gov / apply.gov account active",
        "- [ ] JustGrants account active (DOJ programs)",
        "- [ ] Research.gov account active (NSF SBIR/STTR)",
        "- [ ] SF-424 templates pre-filled",
        "- [ ] Financial statements updated",
        "- [ ] Organizational chart current",
        "- [ ] Key personnel resumes updated",
        "- [ ] Narrative templates ready",
        "- [ ] Budget templates ready",
        "- [ ] 2 CFR 200 financial management policies documented",
        "- [ ] Single-audit readiness (>$750K federal spend)",
        "",
        "**Pre-Registration (do early):**",
        "- [ ] Complete any pre-registration tracked in the pre-registration table above",
        "",
        "---",
        "",
        f"*Dashboard maintained by GrantBot Pipeline — {datetime.utcnow().strftime('%Y-%m-%d')}*",
    ])

    return "\n".join(lines)


def save_dashboard(content: str):
    """Save dashboard to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_FILE, "w") as f:
        f.write(content)
    logger.info(f"Dashboard saved to {DASHBOARD_FILE}")