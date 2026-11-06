"""
Grant Pipeline Orchestrator.

Main entry point that chains: Discover → Filter → Score → Draft → Calendar → Dashboard

Usage:
  python pipeline.py            # Full cycle (network discovery + curated merge)
  python pipeline.py --offline  # No network: load existing DB + curated grants only
"""
from __future__ import annotations
import asyncio
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from models import Grant
from config import GRANTS_DB_FILE, OUTPUT_DIR, DRAFTS_DIR
from discover import discover_all
from curated import get_curated_grants
from filter import filter_and_score
from draft import generate_all_drafts
from calendar_sync import schedule_grant_events
from dashboard import render_dashboard, save_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "pipeline.log", mode="a") if OUTPUT_DIR.exists() else logging.NullHandler(),
    ],
)
logger = logging.getLogger("grantbot.pipeline")


def _merge_grants(*lists: list[Grant]) -> list[Grant]:
    """Merge grant lists, deduplicating by id (later lists win on conflict)."""
    merged: dict[str, Grant] = {}
    for grants in lists:
        for g in grants:
            merged[g.id] = g
    return list(merged.values())


async def run_pipeline(offline: bool = False):
    """Execute the full grant pipeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("GRANT PIPELINE — Starting full cycle" + (" (OFFLINE)" if offline else ""))
    logger.info("=" * 60)

    # Phase 1: DISCOVER
    logger.info("[1/5] Discovering grant opportunities...")
    if offline:
        # Load existing DB (no network) + curated registry
        raw_grants = []
        if GRANTS_DB_FILE.exists():
            with open(GRANTS_DB_FILE) as f:
                raw_grants = [Grant.from_dict(d) for d in json.load(f)]
            logger.info(f"  → loaded {len(raw_grants)} grants from existing DB")
        curated = get_curated_grants()
        logger.info(f"  → {len(curated)} curated grants from registry")
        # Curated registry is authoritative — merge it LAST so it wins on id conflict
        raw_grants = _merge_grants(raw_grants, curated)
    else:
        discovered = await discover_all()
        curated = get_curated_grants()
        logger.info(f"  → {len(discovered)} raw grants discovered, {len(curated)} curated")
        raw_grants = _merge_grants(discovered, curated)
    logger.info(f"  → {len(raw_grants)} total grants")
    stats = {"total_discovered": len(raw_grants)}

    # Phase 2: FILTER & SCORE
    logger.info("[2/5] Filtering and scoring...")
    qualified = filter_and_score(raw_grants)
    logger.info(f"  → {len(qualified)} grants qualified")
    stats["qualified"] = len(qualified)
    stats["excluded"] = stats["total_discovered"] - len(qualified)

    # Realistic cash picture. Only realistic_award_usd is summable —
    # estimated_value carries pool sizes and award ceilings and must not be summed.
    actionable = [g for g in qualified if g.application_ready]
    live_cash = [g for g in actionable if (g.realistic_award_usd or 0) > 0]
    stats["actionable"] = len(actionable)
    stats["realistic_cash_total"] = sum(g.realistic_award_usd for g in live_cash)
    stats["blocked_count"] = sum(1 for g in qualified if g.realistic_award_usd == 0)
    stats["unassessed_count"] = sum(1 for g in qualified if g.realistic_award_usd is None)
    stats["unverified_geo_count"] = sum(1 for g in qualified if not g.geo_verified)

    # Phase 3: DRAFT
    logger.info("[3/5] Generating compliance matrices and drafts...")
    drafts = generate_all_drafts(qualified)
    stats["drafts_generated"] = len(drafts)
    logger.info(f"  → {len(drafts)} draft packages generated")

    # Clean up stale draft files from previous runs (grants no longer tracked)
    generated = set()
    for _, draft in drafts:
        safe_name = draft.grant_name.replace("/", "-").replace(" ", "_")[:60]
        generated.add(f"{safe_name}_{draft.grant_id[:8]}.md")
    removed = 0
    if DRAFTS_DIR.exists():
        for f in DRAFTS_DIR.glob("*.md"):
            if f.name not in generated:
                f.unlink()
                removed += 1
    if removed:
        logger.info(f"  → removed {removed} stale draft files")

    # Phase 4: CALENDAR
    logger.info("[4/5] Synchronizing calendar events...")
    qualified = schedule_grant_events(qualified)
    cal_count = sum(1 for g in qualified if "Scheduled" in g.calendar_status)
    stats["calendar_events"] = cal_count
    logger.info(f"  → {cal_count} calendar events created")

    # Phase 5: DASHBOARD
    logger.info("[5/5] Rendering dashboard...")
    dashboard = render_dashboard(qualified, stats)
    save_dashboard(dashboard)

    # Save grants database
    with open(GRANTS_DB_FILE, "w") as f:
        json.dump([g.to_dict() for g in qualified], f, indent=2)
    logger.info(f"  → Grants DB saved to {GRANTS_DB_FILE}")

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print(f"  Discovered:  {stats['total_discovered']}")
    print(f"  Qualified:   {stats['qualified']}")
    print(f"  Excluded:    {stats['excluded']}")
    print(f"  Actionable:  {stats['actionable']}")
    print(f"  Blocked:     {stats['blocked_count']} (no realistic cash)")
    print(f"  Unassessed:  {stats['unassessed_count']} (no realistic award set)")
    print(f"  Unverified geography: {stats['unverified_geo_count']}")
    print(f"  Drafts:      {stats['drafts_generated']}")
    print(f"  Calendar:    {stats['calendar_events']} events")
    print(f"  Dashboard:   {OUTPUT_DIR / 'grant_dashboard.md'}")
    print("=" * 60)
    print(f"\nREALISTIC CASH (summable): ${stats['realistic_cash_total']:,}")
    print("  NOTE: assumes every live grant is won. Not a forecast.")

    # Print top 5 to stdout
    print("\nTOP OPPORTUNITIES:")
    for i, g in enumerate(qualified[:5], 1):
        print(f"  {i}. [{g.match_score}] {g.name[:60]}")
        print(f"     Funder: {g.funder} | Value: {g.estimated_value}")
        print(f"     Deadline: {g.deadline or 'Rolling'} | Calendar: {g.calendar_status}")
        print()

    return qualified, stats


if __name__ == "__main__":
    offline = "--offline" in sys.argv
    asyncio.run(run_pipeline(offline=offline))
