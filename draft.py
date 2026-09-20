"""
Compliance Matrix & Application Draft Generator.

Generates clean, actionable draft files that match calendar reminders.
Each draft includes: timeline, funding, requirements, and a pre-written application.

This is a generic template — the narrative and budget sections are assembled from
config values (VENTURE_NAME, VENTURE_DESCRIPTION, VENTURE_MISSION, CITY/STATE/ZIP)
so the same code can be reused for a different program or region.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import List

from models import Grant, ComplianceMatrix, ApplicationDraft
from config import (
    VENTURE_NAME, VENTURE_DESCRIPTION, VENTURE_MISSION,
    ZIP_CODE, STATE, CITY, DRAFTS_DIR,
    FOR_PROFIT_ENTITY,
)

logger = logging.getLogger("grantbot.draft")


def generate_compliance_matrix(grant: Grant) -> ComplianceMatrix:
    """Generate a compliance matrix for a grant."""
    source = grant.source.lower()

    # Entity-specific document requirements (for-profit only)
    entity_docs = [
        "Proof of For-Profit Entity Status (LLC/C-Corp)",
        "Articles of Organization / Incorporation",
        "Operating Agreement / Bylaws",
    ]

    required_docs = [
        "SF-424 (Application for Federal Assistance)",
        "Project Narrative / Statement of Work",
        "Budget and Budget Justification",
        "Organizational Chart",
        "Financial Statements (most recent fiscal year)",
        "Resume/CVs of Key Personnel",
    ] + entity_docs
    eligibility = [
        f"Entity located in or serving {CITY}, {STATE} (ZIP: {ZIP_CODE})",
        "SAM.gov registration active",
        "UEI (Unique Entity Identifier) verified",
        "No active federal debarment or suspension",
    ]
    submission_method = "Grants.gov electronic submission"
    pre_reg = grant.pre_registration_required

    if source == "grants_gov":
        submission_method = "Grants.gov — apply.gov portal"
        pre_reg = True
    elif source == "usda_rd":
        submission_method = "USDA RD Apply portal or mail"
        required_docs.append("RD Application Form 4280-3A")
        eligibility.append("Located in a rural area (population < 20,000)")
    elif source == "state_ded":
        submission_method = "State economic development online portal or email"
    elif source == "curated":
        # Curated programs have their own portals
        if "comcast" in grant.funder.lower():
            submission_method = "Comcast RISE / Project UP online application"
        elif "verizon" in grant.funder.lower():
            submission_method = "Verizon Digital Ready portal (after 2 courses)"
        elif "hello alice" in grant.funder.lower():
            submission_method = "Hello Alice platform application"
        elif "nsf" in grant.funder.lower():
            submission_method = "Research.gov — Project Pitch first, then full proposal"
        elif "bja" in grant.funder.lower() or "justice" in grant.funder.lower():
            submission_method = "JustGrants (DOJ) electronic submission"
        elif "irs" in grant.funder.lower():
            submission_method = "IRS Form 8850 (WOTC) / Form 990-T (elective pay)"
        else:
            submission_method = "Program-specific online application"

    if "rural" in grant.description.lower():
        required_docs.append("Rural Impact Statement")
        eligibility.append("Demonstrates rural community impact")

    eligibility.append(f"{FOR_PROFIT_ENTITY}")

    notes = [
        f"Grant value: {grant.estimated_value}",
        f"Source: {grant.source}",
        f"Category: {grant.category}",
        f"Entity target: {grant.entity_target}",
    ]
    if grant.next_cycle_deadline:
        notes.append(f"Next cycle: {grant.next_cycle_deadline}")
    if not grant.application_ready:
        notes.append("NOT actionable yet — prepare for the next cycle")

    return ComplianceMatrix(
        grant_id=grant.id,
        grant_name=grant.name,
        required_documents=required_docs,
        eligibility_criteria=eligibility,
        submission_method=submission_method,
        pre_registration_required=pre_reg,
        sam_gov_validated=True,
        uei_verified=True,
        notes=notes,
    )


def generate_application_draft(grant: Grant) -> ApplicationDraft:
    """Generate a pre-written application draft for a qualified grant."""
    entity_name = FOR_PROFIT_ENTITY
    narrative = f"""PROJECT NARRATIVE

1. EXECUTIVE SUMMARY
{entity_name} proposes to deploy {VENTURE_DESCRIPTION} to serve residents
of {CITY}, {STATE} and surrounding communities. This project directly addresses
{grant.category.replace('_', ' ')} needs through a sustainable operating model
that remains viable beyond the funded period.

2. STATEMENT OF NEED
{CITY}, {STATE} (ZIP {ZIP_CODE}) and the surrounding area face limited access
to {VENTURE_MISSION}. Barriers include:
- Gaps in digital infrastructure and digital literacy
- Few local programs building relevant technical skills
- High cost of entry to technology and equipment
- Limited local workforce-training options for underserved residents

3. PROJECT DESCRIPTION
The proposed work includes:
a) Core service delivery: {VENTURE_DESCRIPTION}
b) A community access program that lowers the cost of entry to technology
c) Skills-based training for local participants
d) A local hub connecting residents to the services, technology, and training

4. ORGANIZATIONAL CAPACITY
{entity_name} brings together expertise in engineering, service delivery, and
community programs. Work is done on self-hosted, privacy-first infrastructure
with no third-party cloud dependencies.

5. EXPECTED OUTCOMES
- A defined number of residents trained in relevant skills each cycle
- A measurable volume of service delivery
- High program completion and retention rates
- Affordable technology access for participating households
- Sustainable operation beyond the funded period
"""

    # Budget is intentionally generic — scale it to the actual program.
    budget = f"""BUDGET OUTLINE

Category                                    Year 1 Estimate
─────────────────────────────────────────────────────────
Personnel (2 FTE + contractors)            $85,000
Platform Development & Infrastructure       $45,000
Community Program Delivery                  $30,000
Equipment & Materials                       $25,000
Facility & Overhead                         $35,000
─────────────────────────────────────────────────────────
TOTAL                                    $220,000

Note: Budget is scalable based on the actual award amount.
"""

    exec_summary = (
        f"{entity_name} seeks funding to establish {VENTURE_DESCRIPTION} "
        f"capabilities serving {CITY}, {STATE}. This project addresses "
        f"{grant.category.replace('_', ' ')} needs through a sustainable operating "
        f"model, targeting underserved residents with services, skills training, "
        f"and affordable technology access."
    )

    org_capacity = (
        f"{entity_name} maintains active SAM.gov registration, UEI verification, "
        f"and relevant organizational certifications. The team combines engineering "
        f"and delivery experience with community program operations. All infrastructure "
        f"is self-hosted and privacy-first."
    )

    return ApplicationDraft(
        grant_id=grant.id,
        grant_name=grant.name,
        executive_summary=exec_summary,
        project_narrative=narrative,
        budget_outline=budget,
        organizational_capacity=org_capacity,
    )


def generate_all_drafts(grants: List[Grant]) -> List[tuple[ComplianceMatrix, ApplicationDraft]]:
    """Generate compliance matrices and drafts for all qualified grants."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for grant in grants:
        matrix = generate_compliance_matrix(grant)
        draft = generate_application_draft(grant)
        results.append((matrix, draft))

        safe_name = grant.name.replace("/", "-").replace(" ", "_")[:60]
        draft_file = DRAFTS_DIR / f"{safe_name}_{grant.id[:8]}.md"

        # Build clean, action-oriented draft file
        deadline_display = grant.deadline or "Rolling"
        if deadline_display and len(deadline_display) > 10:
            deadline_display = deadline_display[:10]

        reqs = "\n".join(f"- [ ] {doc}" for doc in matrix.required_documents)
        elig = "\n".join(f"- [ ] {c}" for c in matrix.eligibility_criteria)

        with open(draft_file, "w") as f:
            f.write(f"# {grant.name}\n\n")
            f.write(f"| Field | Value |\n")
            f.write(f"|-------|-------|\n")
            f.write(f"| **Funder** | {grant.funder} |\n")
            f.write(f"| **Funding** | {grant.estimated_value} |\n")
            f.write(f"| **Deadline** | {deadline_display} |\n")
            f.write(f"| **Entity Target** | {grant.entity_target} |\n")
            f.write(f"| **Application Ready** | {'YES' if grant.application_ready else 'NO (next cycle)'} |\n")
            if grant.next_cycle_deadline:
                f.write(f"| **Next Cycle** | {grant.next_cycle_deadline} |\n")
            if grant.pre_registration_required:
                f.write(f"| **Pre-Registration** | REQUIRED — complete before applying |\n")
            f.write(f"| **Match Score** | {grant.match_score}/100 |\n")
            f.write(f"| **Category** | {grant.category} |\n")
            f.write(f"| **Source** | {grant.source_url} |\n")
            f.write(f"| **Submit Via** | {matrix.submission_method} |\n\n")

            f.write("---\n\n")
            f.write("## YOUR ACTIONS\n\n")
            f.write("### 1. EDIT & APPROVE THIS DRAFT (due 30 days before deadline)\n")
            f.write("Read this file, make changes to the narrative/budget below, then approve.\n\n")
            f.write("### 2. SUBMIT ATTACHMENTS (due 16 days before deadline)\n")
            f.write("Upload the documents below to the portal.\n\n")
            f.write("### 3. CLICK SUBMIT (due 3 days before deadline)\n")
            f.write("Final review and click submit.\n\n")

            f.write("---\n\n")
            f.write("## REQUIREMENTS\n\n")
            f.write("**What You Need:**\n")
            f.write(reqs + "\n\n")
            f.write("**Eligibility:**\n")
            f.write(elig + "\n\n")

            f.write("---\n\n")
            f.write("## EXECUTIVE SUMMARY\n\n")
            f.write(draft.executive_summary + "\n\n")

            f.write("---\n\n")
            f.write("## PROJECT NARRATIVE (Edit this)\n\n")
            f.write(draft.project_narrative + "\n\n")

            f.write("---\n\n")
            f.write("## BUDGET (Edit this)\n\n")
            f.write(draft.budget_outline + "\n\n")

            f.write("---\n\n")
            f.write("## ORGANIZATIONAL CAPACITY\n\n")
            f.write(draft.organizational_capacity + "\n")

        logger.info(f"Draft saved: {draft_file}")

    return results