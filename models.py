"""
Data models for the Grant Pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class Grant:
    """Represents a single discovered grant opportunity."""
    id: str
    name: str
    funder: str
    description: str
    estimated_value: str = "Unknown"
    use_type: str = "General"          # General | Restricted
    deadline: Optional[str] = None     # ISO date or "Rolling"
    source_url: str = ""
    source: str = ""                   # grants_gov, sam_gov, etc.
    category: str = ""
    match_score: float = 0.0
    calendar_status: str = "Not Scheduled"
    calendar_event_id: Optional[str] = None
    geographic_eligible: bool = True
    exclusion_flagged: bool = False
    exclusion_reason: str = ""
    # ── Entity targeting ─────────────────────────────────
    entity_target: str = "both"          # for_profit | nonprofit | both
    # ── Application readiness / next-cycle tracking ──────
    pre_registration_required: bool = False
    application_ready: bool = True       # False if deadline is before APPLICATION_READY_DATE
    next_cycle_deadline: Optional[str] = None  # ISO date of the next open cycle
    notes: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Grant:
        d.pop("raw_data", None)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ComplianceMatrix:
    """Compliance checklist for a grant application."""
    grant_id: str
    grant_name: str
    required_documents: list[str] = field(default_factory=list)
    eligibility_criteria: list[str] = field(default_factory=list)
    submission_method: str = ""
    pre_registration_required: bool = False
    sam_gov_validated: bool = False
    uei_verified: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class ApplicationDraft:
    """Pre-written application draft for a grant."""
    grant_id: str
    grant_name: str
    executive_summary: str = ""
    project_narrative: str = ""
    budget_outline: str = ""
    organizational_capacity: str = ""
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
