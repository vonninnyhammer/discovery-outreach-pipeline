"""
Curated Grant Registry — Verified Research.

Manually maintained list of grants researched and verified for a technology /
workforce-development venture. These are NOT scraped — they are the known-good
targets. Merged into the pipeline alongside discovery.

Each entry carries entity targeting (for_profit / nonprofit / both), 
pre-registration flags, and next-cycle deadlines for programs whose current
cycle closes before APPLICATION_READY_DATE.
"""
from __future__ import annotations
from typing import List

from models import Grant

# ── Federal ────────────────────────────────────────────────────────────────
FEDERAL = [
    dict(
        id="curated-nsf-sbir-sttr",
        name="NSF SBIR/STTR Phase I (AI/ML R&D)",
        funder="National Science Foundation",
        description=(
            "Small Business Innovation Research / Technology Transfer for AI and "
            "machine learning R&D. Relaunched May 2026 with $250M. Phase I up to "
            "$305K, Phase II up to $1.25M. For-profit only: <500 employees, 51%+ "
            "US-owned, PI employed >50%. Project Pitch required before full proposal."
        ),
        estimated_value="Phase I $305K / Phase II $1M+",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://seedfund.nsf.gov",
        source="curated",
        category="ai_tech_innovation",
        entity_target="for_profit",
        next_cycle_deadline="2027-01-06",
        notes=[
            "Project Pitch is rolling; full proposals due at 3 annual deadlines (next ~Jan 2027).",
            "For-profit arm only. PI must be employed >50% by the company.",
            "Relaunched May 2026 — verify current solicitation number.",
        ],
    ),
    dict(
        id="curated-usda-rbdg",
        name="USDA Rural Business Development Grant (RBDG)",
        funder="USDA Rural Development",
        description=(
            "Grants for rural business development, technical assistance, and "
            "training. FY26 ~$27.7M. Nonprofit 501(c)(3) serving rural areas "
            "eligible. No match required, but leverage earns points. Service "
            "area qualifies as rural."
        ),
        estimated_value="Up to $5M+ (FY26 pool $27.7M)",
        use_type="Restricted",
        deadline="2026-06-30",
        source_url="https://www.rd.usda.gov/programs-services/business-programs/rural-business-development-grants",
        source="curated",
        category="rural_development",
        entity_target="nonprofit",
        next_cycle_deadline="2027-06-30",
        notes=[
            "FY26 cycle closed June 30, 2026 — target FY27 (NOFO typically spring, deadline ~June).",
            "Nonprofit arm only. No match required; leverage/partnerships earn points.",
            "Service area qualifies as rural (<50K population).",
        ],
    ),
    dict(
        id="curated-usda-reap",
        name="USDA REAP (Renewable Energy for America Program) — Loans",
        funder="USDA Rural Development",
        description=(
            "Loans for renewable energy systems (solar) and energy efficiency "
            "improvements. GRANTS are PAUSED in 2026 (EO 14315); guaranteed loans "
            "remain active. For-profit businesses eligible; nonprofits generally "
            "ineligible. Covers solar for the facility."
        ),
        estimated_value="Loans up to 75% of project cost",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://www.rd.usda.gov/programs-services/energy-programs/rural-energy-america-program-renewable-energy-systems-energy-efficiency-improvement-guaranteed-loans",
        source="curated",
        category="energy_renewables",
        entity_target="for_profit",
        notes=[
            "Grant component PAUSED 2026 (EO 14315) — loans still active.",
            "For-profit arm only. Solar qualifies; verify equipment eligibility.",
        ],
    ),
    dict(
        id="curated-dol-reo",
        name="DOL Reentry Employment Opportunities (REO)",
        funder="U.S. Department of Labor (ETA)",
        description=(
            "Workforce development for justice-involved individuals: youth 15-18, "
            "young adults 18-24, adults 18+. PY2026 $110M. Community/faith-based "
            "organizations eligible. AI/digital literacy training is fundable. "
            "Aligns with reentry hiring mission."
        ),
        estimated_value="Awards up to $5M+ (PY26 pool $110M)",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://www.dol.gov/grants",
        source="curated",
        category="reentry_rehabilitation",
        entity_target="nonprofit",
        next_cycle_deadline="2027-05-01",
        notes=[
            "PY2026 FOA active — verify exact deadline; next cycle PY2027 (~spring 2027).",
            "Nonprofit arm. AI/digital literacy training explicitly fundable.",
        ],
    ),
    dict(
        id="curated-dol-restart",
        name="DOL RESTART (Reentry, Skills, Training, And Reentry Transition)",
        funder="U.S. Department of Labor (ETA)",
        description=(
            "FY26 $81M, ~20 awards of $1M-$5.1M. AI infrastructure occupations "
            "included. States and intermediaries eligible; nonprofits can partner "
            "or apply as intermediaries. Reentry workforce focus."
        ),
        estimated_value="$1M - $5.1M per award",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://www.dol.gov/grants",
        source="curated",
        category="reentry_rehabilitation",
        entity_target="nonprofit",
        notes=[
            "FY26 FOA open — verify exact deadline; next cycle FY27 if missed.",
            "AI infrastructure occupations included — strong fit for AI/tech training.",
        ],
    ),
    dict(
        id="curated-bja-sca-reentry-ed",
        name="BJA Second Chance Act: Improving Reentry Education & Employment",
        funder="Bureau of Justice Assistance (DOJ)",
        description=(
            "FY26 ~$9M for reentry education and employment programs. Nonprofits "
            "AND for-profits eligible. MOU with corrections agency required "
            "(longest lead-time item — start early). FY26 deadline was Sept/Oct 2026."
        ),
        estimated_value="Awards up to $1M+ (FY26 ~$9M)",
        use_type="Restricted",
        deadline="2026-09-24",
        source_url="https://bja.ojp.gov/funding/opportunities/o-bja-2026-172126",
        source="curated",
        category="reentry_rehabilitation",
        entity_target="both",
        next_cycle_deadline="2027-09-01",
        notes=[
            "FY26 cycle closed (grants.gov 09/24/2026, JustGrants 10/01/2026) — target FY27.",
            "MOU with corrections agency required — begin conversations now.",
            "Both entities eligible; nonprofit arm is the natural applicant.",
        ],
    ),
    dict(
        id="curated-bja-sca-tech-careers",
        name="BJA Second Chance Act: Technology Careers Training",
        funder="Bureau of Justice Assistance (DOJ)",
        description=(
            "Up to $750K for technology careers training for justice-involved "
            "individuals. Nonprofits eligible. Direct fit for IT/AI certification "
            "training for reentry hires."
        ),
        estimated_value="Up to $750,000",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://bja.ojp.gov/funding/opportunities",
        source="curated",
        category="reentry_rehabilitation",
        entity_target="nonprofit",
        next_cycle_deadline="2027-09-01",
        notes=[
            "Next cycle expected FY27 (~fall 2027).",
            "Nonprofit arm. Technology careers training for justice-involved individuals.",
        ],
    ),
    dict(
        id="curated-eda-pweaa",
        name="EDA Public Works & Economic Adjustment Assistance (PWEAA)",
        funder="U.S. Economic Development Administration",
        description=(
            "$100K-$30M for infrastructure and economic development. Nonprofit "
            "needs local government cooperation letter; ~50% match; CEDS "
            "alignment required. FY26 rolling NOFO. For-profits ineligible."
        ),
        estimated_value="$100K - $30M",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://www.eda.gov/funding-opportunities",
        source="curated",
        category="infrastructure",
        entity_target="nonprofit",
        notes=[
            "Rolling NOFO — can apply anytime after Nov 2026.",
            "Nonprofit arm. Local govt cooperation letter + CEDS alignment needed.",
            "Good fit for facility/build-out and solar infrastructure.",
        ],
    ),
    dict(
        id="curated-wotc",
        name="Work Opportunity Tax Credit (WOTC) — Ex-Felon & Youth",
        funder="IRS / DOL",
        description=(
            "Tax credit for hiring targeted groups: ex-felons up to $2,400 (40% of "
            "$6K first-year wages), youth up to $1,200. CREDIT LAPSED Jan 1, 2026 — "
            "keep filing Form 8850 within 28 days of hire for retroactive renewal. "
            "Per-hire, rolling."
        ),
        estimated_value="Up to $2,400 per hire",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://www.irs.gov/businesses/small-businesses-self-employed/work-opportunity-tax-credit",
        source="curated",
        category="workforce_training",
        entity_target="for_profit",
        notes=[
            "Lapsed Jan 1, 2026 — file Form 8850 within 28 days of hire regardless.",
            "For-profit arm. Ex-felon $2,400 / youth $1,200 per hire.",
        ],
    ),
    dict(
        id="curated-federal-bonding",
        name="Federal Bonding Program",
        funder="U.S. Department of Labor",
        description=(
            "Free fidelity bonds covering the first 6 months of employment for "
            "at-risk hires (ex-offenders, etc.). No cost to employer or employee. "
            "Rolling, per-hire. Removes hiring risk for reentry hires."
        ),
        estimated_value="Free fidelity bonds (first 6 months)",
        use_type="General",
        deadline="Rolling",
        source_url="https://www.dol.gov/agencies/eta/federal-bonding",
        source="curated",
        category="workforce_training",
        entity_target="for_profit",
        notes=[
            "Rolling, per-hire. Use for every reentry hire.",
            "For-profit arm. No cost.",
        ],
    ),
    dict(
        id="curated-solar-itc-elective-pay",
        name="Solar Investment Tax Credit — Elective Pay (IRA 6417)",
        funder="IRS",
        description=(
            "30% direct cash payment for solar (<1MW) via elective pay. Nonprofits "
            "eligible (no tax liability needed). OBBBA deadline: construction-start "
            "path closed July 4, 2026 — placed-in-service by Dec 31, 2027 only. "
            "Only net-zero generation qualifies for 48E."
        ),
        estimated_value="30% direct pay (up to $1M+)",
        use_type="Restricted",
        deadline="2027-12-31",
        source_url="https://www.irs.gov/credits-deductions/elective-pay-and-transferability-credits",
        source="curated",
        category="energy_renewables",
        entity_target="nonprofit",
        notes=[
            "Nonprofit arm (no tax liability needed). Solar only — other generators must be verified.",
            "Placed-in-service by Dec 31, 2027 (construction-start path closed).",
            "Domestic content bonus phases out for >1MW systems.",
        ],
    ),
]

# ── Corporate / Pre-Registration ───────────────────────────────────────────
CORPORATE = [
    dict(
        id="curated-comcast-rise",
        name="Comcast RISE",
        funder="Comcast",
        description=(
            "$5K cash + tech makeover + TV commercial + media schedule (~$30K+ "
            "total). For-profit, <=100 employees, 2+ years operating, 12+ months "
            "revenue. Owner no felony convictions past 10 years. Zip-based rounds "
            "(geography rotates by round). Annual May 1-31 window."
        ),
        estimated_value="$5K cash + ~$30K+ package",
        use_type="General",
        deadline="2027-05-31",
        source_url="https://www.comcastrise.com",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        pre_registration_required=True,
        next_cycle_deadline="2027-05-31",
        notes=[
            "PRE-REGISTRATION: two-part application — complete eligibility form early.",
            "Annual May 1-31 window — next: May 2027.",
            "For-profit arm only. Nonprofits excluded.",
            "Geography rotates by round — verify your ZIP is included in the current round.",
            "Owner felony rule: no convictions past 10 years — verify against reentry hires.",
        ],
    ),
    dict(
        id="curated-verizon-digital-ready",
        name="Verizon Small Business Digital Ready",
        funder="Verizon / LISC",
        description=(
            "$10K grants, 10/month June-Dec 2026 (70 total). Register + complete "
            "any 2 free courses/events to unlock eligibility. For-profit only. "
            "Apply once, remain eligible all year. Final decision Jan 12, 2027. "
            "2027 cycle expected early 2027."
        ),
        estimated_value="$10,000",
        use_type="General",
        deadline="Rolling",
        source_url="https://digitalready.verizonwireless.com",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        pre_registration_required=True,
        notes=[
            "PRE-REGISTRATION: create account + complete 2 free courses/events to unlock.",
            "For-profit arm only. 2026 cycle open now; 2027 cycle expected early 2027.",
            "Apply once, remain eligible all year.",
        ],
    ),
    dict(
        id="curated-hello-alice",
        name="Hello Alice Grants",
        funder="Hello Alice",
        description=(
            "Free platform aggregating small business grants ($5K-$25K+). Multiple "
            "cycles year-round. For-profit businesses. Pre-registration required "
            "(free account). Good pipeline source for corporate grants."
        ),
        estimated_value="$5K - $25K",
        use_type="General",
        deadline="Rolling",
        source_url="https://www.helloalice.com",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        pre_registration_required=True,
        notes=[
            "PRE-REGISTRATION: free Hello Alice account required.",
            "For-profit arm. Aggregates multiple grant cycles year-round.",
        ],
    ),
    dict(
        id="curated-amber-grant",
        name="Amber Grant",
        funder="WomensNet",
        description=(
            "$10K monthly (3 awards) + $50K year-end (3 awards). Women-owned "
            "businesses (>=50% ownership). $15 application fee. Monthly rolling "
            "deadlines."
        ),
        estimated_value="$10,000 monthly / $50,000 year-end",
        use_type="General",
        deadline="Rolling",
        source_url="https://ambergrantsforwomen.com",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        notes=[
            "Monthly rolling deadlines — apply anytime after Nov 2026.",
            "For-profit arm. Requires >=50% women ownership.",
            "$15 application fee.",
        ],
    ),
    dict(
        id="curated-nase-growth",
        name="NASE Growth Grant",
        funder="National Association for the Self-Employed",
        description=(
            "Up to $4,000 for business growth. Requires paid NASE membership "
            "(~$150/yr). Rolling. For-profit businesses."
        ),
        estimated_value="Up to $4,000",
        use_type="General",
        deadline="Rolling",
        source_url="https://www.nase.org",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        notes=[
            "Rolling. Requires paid NASE membership.",
            "For-profit arm.",
        ],
    ),
    dict(
        id="curated-fedex-grant-contest",
        name="FedEx Small Business Grant Contest",
        funder="FedEx",
        description=(
            "$50K grand prize + additional awards. Annual contest. 2026 dates TBD "
            "— monitor. For-profit small businesses."
        ),
        estimated_value="$50,000 grand prize",
        use_type="General",
        deadline="Rolling",
        source_url="https://www.fedex.com/en-us/small-business/grant-contest.html",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        notes=[
            "2026 dates TBD — monitor; next cycle expected 2027.",
            "For-profit arm.",
        ],
    ),
    dict(
        id="curated-allstate-main-street",
        name="Allstate Main Street Grants",
        funder="Allstate",
        description=(
            "$20K grants for small businesses. Requires $25K+ prior-year revenue. "
            "Periodic cycles. For-profit businesses."
        ),
        estimated_value="$20,000",
        use_type="General",
        deadline="Rolling",
        source_url="https://www.allstate.com/main-street",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        notes=[
            "Periodic cycles — monitor for next window.",
            "For-profit arm. $25K+ prior-year revenue required.",
        ],
    ),
    dict(
        id="curated-jobber-grants",
        name="Jobber Grants",
        funder="Jobber",
        description=(
            "$250K pool, $100K top prize. Annual. 2026 Phase 1 closed June 11 — "
            "next cycle expected ~June 2027. For-profit home service businesses."
        ),
        estimated_value="$250K pool / $100K top",
        use_type="General",
        deadline="Rolling",
        source_url="https://getjobber.com/grants",
        source="curated",
        category="corporate_small_business",
        entity_target="for_profit",
        next_cycle_deadline="2027-06-01",
        notes=[
            "Annual — next cycle expected ~June 2027.",
            "For-profit arm.",
        ],
    ),
    dict(
        id="curated-comcast-digital-equity",
        name="Comcast Digital Equity Grants (Project UP)",
        funder="Comcast",
        description=(
            "$30K-$200K+ for nonprofits advancing digital equity. Part of $1B "
            "Project UP commitment (1,250+ Lift Zones, 14,500 RISE recipients). "
            "Ongoing via local Comcast market teams. Lift Zones = free WiFi in "
            "community centers — fits the digital hub."
        ),
        estimated_value="$30,000 - $200,000+",
        use_type="Restricted",
        deadline="Rolling",
        source_url="https://corporate.comcast.com/impact/project-up",
        source="curated",
        category="digital_inclusion",
        entity_target="nonprofit",
        notes=[
            "Ongoing — apply via local Comcast market team.",
            "Nonprofit arm. Lift Zones program fits the community digital hub.",
        ],
    ),
    dict(
        id="curated-viapath-foundation",
        name="ViaPath Foundation Impact Grant",
        funder="ViaPath Foundation",
        description=(
            "Annual grant for reentry-focused programs. Window Jan 26-Feb 20 each "
            "year. Nonprofits. Direct fit for reentry hiring + technology training."
        ),
        estimated_value="Varies (reentry-focused)",
        use_type="Restricted",
        deadline="2027-02-20",
        source_url="https://viapathfoundation.org",
        source="curated",
        category="reentry_rehabilitation",
        entity_target="nonprofit",
        next_cycle_deadline="2027-02-20",
        notes=[
            "Annual window Jan 26-Feb 20 — next: 2027.",
            "Nonprofit arm. Reentry-focused.",
        ],
    ),
]

ALL_CURATED = FEDERAL + CORPORATE


def get_curated_grants() -> List[Grant]:
    """Build Grant objects from the curated registry."""
    grants = []
    for entry in ALL_CURATED:
        grants.append(Grant(**entry))
    return grants