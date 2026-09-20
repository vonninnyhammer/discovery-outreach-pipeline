"""
Local & Regional Resources Registry — example data.

A neutral example of the resource registry consumed by the dashboard stage.
Replace the entries here with resources relevant to your own area. The shape
is the contract: name, org, kind, amount, terms, fit, use_by, status.
"""
from __future__ import annotations

RESOURCES = [
    {
        "name": "Example Small Business Development Center",
        "org": "Example SBDC affiliate",
        "kind": "free_assistance",
        "entity_needed": False,
        "amount": "Free one-on-one consulting",
        "terms": "No cost; publicly funded",
        "fit": "Business planning, financials, and program navigation for local applicants.",
        "use_by": "Week 1-4 (start immediately)",
        "status": "open",
    },
    {
        "name": "Example Regional Revolving Loan Fund",
        "org": "Example Council of Governments",
        "kind": "loan",
        "entity_needed": True,
        "amount": "Varies by program",
        "terms": "Real business collateral and repayment plan required",
        "fit": "Equipment and build-out financing for a registered business.",
        "use_by": "Post-registration",
        "status": "open",
    },
    {
        "name": "Example USDA Rural Business program",
        "org": "Example state USDA Rural Development office",
        "kind": "assistance",
        "entity_needed": True,
        "amount": "Program-dependent",
        "terms": "Rural location eligibility required",
        "fit": "Rural-focused business assistance and lending.",
        "use_by": "Post-registration",
        "status": "open",
    },
]

EXAMPLES = [
    "ED, SBA, and USDA-affiliated assistance.",
    "Regional revolving loan funds.",
    "State small-business development affiliates.",
]


def get_local_regional_resources() -> list[dict]:
    """Return the curated local/regional resource list."""
    return RESOURCES


def summarize() -> str:
    """One-line summary for the outreach stage."""
    return "; ".join(EXAMPLES)