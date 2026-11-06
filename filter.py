"""
Filtering, Scoring, and Exclusion Engine.

Applies geographic eligibility, category matching, workforce relevance,
funding analysis, deadline feasibility, and hard exclusion filters.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timedelta
from typing import List

from models import Grant
from config import (
    ZIP_CODE, STATE, COUNTY, TARGET_CATEGORIES,
    SCORING_WEIGHTS, EXCLUSION_KEYWORDS, APPLICATION_READY_DATE,
    ENTITY_TARGETS, _parse_date, _effective_deadline,
)

logger = logging.getLogger("grantbot.filter")


def _check_geographic_eligibility(grant: Grant) -> tuple[bool, bool]:
    """Check geographic eligibility for the configured area.

    Returns (eligible, verified). `verified` is True only when an affirmative
    signal was found. The final fallthrough returns (True, False): no
    disqualifying keyword is absence of evidence, not evidence of eligibility.
    """
    text = f"{grant.description} {grant.name} {grant.funder}".lower()
    # Federal grants are generally eligible
    if grant.funder.lower() in ("federal", "usda rural development"):
        return True, True
    # State-level grants (matching the configured STATE as a whole word)
    if re.search(rf"\b{re.escape(STATE.lower())}\b", text) or grant.source == "state_ded":
        return True, True
    # Rural/distressed preference grants
    rural_signals = ["rural", "distressed", "underserved", "small community",
                     "economically disadvantaged", "rural area"]
    for signal in rural_signals:
        if signal in text:
            return True, True
    # Grants that don't mention geography are typically eligible
    geo_mentions = ["urban", "city only", "metropolitan", "large city",
                    "population over 500", "non-rural"]
    for mention in geo_mentions:
        if mention in text and "rural" not in text:
            return False, False
    return True, False


def _check_exclusion(grant: Grant) -> tuple[bool, str]:
    """Hard exclusion filter. Returns (excluded, reason)."""
    text = f"{grant.description} {grant.name}".lower()
    for keyword in EXCLUSION_KEYWORDS:
        if keyword in text:
            return True, f"Exclusion keyword matched: '{keyword}'"
    return False, ""


def _check_entity_target(grant: Grant) -> tuple[bool, str]:
    """For-profit-only gate. Drops any grant requiring a nonprofit entity.
    'both' is excluded too — it implies nonprofit eligibility/paperwork."""
    target = (grant.entity_target or "both").lower()
    if target not in ENTITY_TARGETS:
        return True, f"Entity target '{target}' not in allowed set {ENTITY_TARGETS}"
    return False, ""


def _calculate_score(grant: Grant) -> float:
    """Calculate weighted match score (0-100)."""
    scores = {}

    # Geographic match (20 pts) — unverified eligibility scores half credit
    geo_ok, geo_ver = _check_geographic_eligibility(grant)
    scores["geographic_match"] = (
        SCORING_WEIGHTS["geographic_match"] if geo_ver
        else SCORING_WEIGHTS["geographic_match"] * 0.5 if geo_ok
        else 0
    )

    # Category alignment (25 pts)
    if grant.category in TARGET_CATEGORIES:
        scores["category_alignment"] = SCORING_WEIGHTS["category_alignment"]
    else:
        scores["category_alignment"] = 5  # partial credit

    # Workforce relevance (20 pts)
    wf_signals = ["workforce", "training", "youth", "foster", "reentry",
                  "rehabilitation", "low-income", "underserved", "education"]
    text_lower = f"{grant.description} {grant.name}".lower()
    wf_hits = sum(1 for s in wf_signals if s in text_lower)
    scores["workforce_relevance"] = min(
        SCORING_WEIGHTS["workforce_relevance"],
        int(wf_hits * (SCORING_WEIGHTS["workforce_relevance"] / len(wf_signals) * 2))
    )

    # Funding amount (10 pts)
    value = grant.estimated_value.lower() if grant.estimated_value else ""
    if any(x in value for x in ["$100k", "$500k", "$1m", "$5m", "100,000", "500,000", "1,000,000"]):
        scores["funding_amount"] = 10
    elif any(x in value for x in ["$10k", "$50k", "10,000", "50,000"]):
        scores["funding_amount"] = 6
    elif value and value not in ("unknown", "varies", ""):
        scores["funding_amount"] = 4
    else:
        scores["funding_amount"] = 2

    # Deadline feasibility (15 pts) — score against effective (next-cycle) deadline
    eff_deadline = _effective_deadline(grant)
    if eff_deadline and eff_deadline != "Rolling":
        dl = _parse_date(eff_deadline)
        if dl is not None:
            days_left = (dl - datetime.now(dl.tzinfo)).days
            if days_left > 60:
                scores["deadline_feasibility"] = 15
            elif days_left > 30:
                scores["deadline_feasibility"] = 10
            elif days_left > 14:
                scores["deadline_feasibility"] = 7
            elif days_left > 0:
                scores["deadline_feasibility"] = 3
            else:
                scores["deadline_feasibility"] = 0
        else:
            scores["deadline_feasibility"] = 8
    else:
        scores["deadline_feasibility"] = 12  # Rolling = good

    # Rolling/micro bonus (10 pts)
    if grant.deadline == "Rolling" or "micro" in text_lower or "no deadline" in text_lower:
        scores["rolling_or_micro"] = 10
    else:
        scores["rolling_or_micro"] = 3

    total = sum(scores.values())
    max_total = sum(SCORING_WEIGHTS.values())
    return round((total / max_total) * 100, 1)


def filter_and_score(grants: List[Grant]) -> List[Grant]:
    """Apply all filters and scoring to a list of grants. Returns qualified grants."""
    qualified = []
    for grant in grants:
        # HARD EXCLUSION
        excluded, reason = _check_exclusion(grant)
        if excluded:
            grant.exclusion_flagged = True
            grant.exclusion_reason = reason
            logger.info(f"EXCLUDED: {grant.name} — {reason}")
            continue

        # ENTITY TARGET — for-profit only
        excluded, reason = _check_entity_target(grant)
        if excluded:
            grant.exclusion_flagged = True
            grant.exclusion_reason = reason
            logger.info(f"ENTITY-EXCLUDED: {grant.name} — {reason}")
            continue

        # Geographic eligibility
        grant.geographic_eligible, grant.geo_verified = _check_geographic_eligibility(grant)
        if not grant.geographic_eligible:
            logger.info(f"GEO-REJECTED: {grant.name}")
            continue

        # Score
        grant.match_score = _calculate_score(grant)

        # Application readiness: flag grants whose deadline is before
        # APPLICATION_READY_DATE as next-cycle (not actionable now).
        if grant.deadline and grant.deadline != "Rolling":
            dl = _parse_date(grant.deadline)
            if dl is not None:
                ready = _parse_date(APPLICATION_READY_DATE)
                if dl < ready:
                    grant.application_ready = False
                    if not grant.next_cycle_deadline:
                        grant.next_cycle_deadline = "TBD — next cycle"

        qualified.append(grant)

    # Sort by score descending
    qualified.sort(key=lambda g: g.match_score, reverse=True)
    logger.info(f"Qualified: {len(qualified)}/{len(grants)} grants after filtering")
    return qualified
