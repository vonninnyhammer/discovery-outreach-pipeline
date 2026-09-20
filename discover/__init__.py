"""
Discovery Module — Scrapes and discovers open funding opportunities from multiple public sources.

Sources:
  - Grants.gov API (api.grants.gov/v1/api/search2 — no auth needed)
  - Simpler.Grants.gov API (api.simpler.grants.gov — needs API key)
  - USDA Rural Development (web search fallback)
  - State economic development portals (web search fallback)
  - Corporate/Foundation programs (web search fallback)
"""
from __future__ import annotations
import httpx
import json
import hashlib
import logging
import asyncio
from datetime import datetime
from typing import List, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models import Grant
from config import SOURCES, ZIP_CODE, STATE, TARGET_CATEGORIES

logger = logging.getLogger("grantbot.discover")

# Search keywords grouped by target category
SEARCH_KEYWORDS = {
    "ai_tech_innovation": [
        "artificial intelligence", "machine learning", "data science",
        "technology innovation", "tech workforce",
    ],
    "small_business": [
        "small business", "SBIR", "STTR", "startup", "entrepreneur",
    ],
    "rural_development": [
        "rural development", "rural community", "rural economic",
        "rural broadband", "distressed community",
    ],
    "workforce_training": [
        "workforce training", "job training", "career training",
        "youth training", "certification program",
    ],
    "digital_inclusion": [
        "digital inclusion", "digital literacy", "broadband access",
        "technology access", "digital divide",
    ],
    "medical_data": [
        "health data", "medical records", "clinical data",
        "health informatics", "telehealth",
    ],
    "government_legal_tech": [
        "legal technology", "government technology", "justice system",
        "court technology", "legal aid",
    ],
    "youth_development": [
        "youth development", "foster care", "youth employment",
        "young adults", "youth workforce",
    ],
    "reentry_rehabilitation": [
        "reentry", "re-entry", "second chance", "rehabilitation workforce",
        "justice-involved",
    ],
}


def _make_id(name: str, funder: str) -> str:
    raw = f"{name}:{funder}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _categorize(text: str) -> str:
    """Map grant text to a target category."""
    text_lower = text.lower()
    category_signals = {
        "ai_tech_innovation": ["artificial intelligence", "ai ", "machine learning", "tech innovation", "data science"],
        "small_business": ["small business", "sbir", "sttr", "entrepreneur", "startup"],
        "government_legal_tech": ["legal", "justice", "court", "government technology", "legal tech"],
        "medical_data": ["health", "medical", "clinical", "patient data", "healthcare"],
        "rural_development": ["rural", "community development", "distressed", "underserved"],
        "infrastructure": ["infrastructure", "broadband", "facility", "building", "construction"],
        "workforce_training": ["workforce", "training", "education", "certification", "job"],
        "charitable_training": ["charitable", "nonprofit", "community service", "social"],
        "digital_inclusion": ["digital", "connectivity", "access", "computer", "internet"],
        "youth_development": ["youth", "young people", "teen", "foster", "student"],
        "reentry_rehabilitation": ["reentry", "re-entry", "rehabilitation", "second chance", "justice-involved"],
    }
    for cat, signals in category_signals.items():
        for signal in signals:
            if signal in text_lower:
                return cat
    return "general"


async def scrape_grants_gov(client: httpx.AsyncClient) -> List[Grant]:
    """Search Grants.gov using the public search2 API endpoint."""
    grants = []
    api_url = "https://api.grants.gov/v1/api/search2"

    # Collect all unique keywords
    all_keywords = []
    for kw_list in SEARCH_KEYWORDS.values():
        all_keywords.extend(kw_list)

    # Deduplicate while preserving order
    seen_kw = set()
    unique_keywords = []
    for kw in all_keywords:
        if kw.lower() not in seen_kw:
            seen_kw.add(kw.lower())
            unique_keywords.append(kw)

    for keyword in unique_keywords:
        try:
            payload = {
                "keyword": keyword,
                "oppStatus": "posted,forecasted",
                "rows": 10,
                "sortBy": "openDate|desc",
            }
            resp = await client.post(api_url, json=payload, timeout=20.0)
            if resp.status_code == 200:
                data = resp.json()
                opps = data.get("data", {}).get("oppHits", [])
                if not opps:
                    opps = data.get("oppHits", [])
                for opp in opps:
                    grant = Grant(
                        id=_make_id(opp.get("title", ""), opp.get("agency", "")),
                        name=opp.get("title", "Unknown"),
                        funder=opp.get("agency", "Federal"),
                        description=opp.get("synopsis", opp.get("description", "")),
                        estimated_value=opp.get("estFund", opp.get("award_ceiling", "Unknown")),
                        deadline=opp.get("closeDate", opp.get("close_date", None)),
                        source_url=f"https://www.grants.gov/search-results-detail/{opp.get('id', opp.get('opportunity_id', ''))}",
                        source="grants_gov",
                        category=_categorize(opp.get("title", "") + " " + opp.get("synopsis", opp.get("description", ""))),
                        raw_data=opp,
                    )
                    grants.append(grant)
            elif resp.status_code == 302:
                # Follow redirects
                location = resp.headers.get("Location", "")
                if location:
                    resp2 = await client.post(location, json=payload, timeout=20.0)
                    if resp2.status_code == 200:
                        data = resp2.json()
                        opps = data.get("data", {}).get("oppHits", []) or data.get("oppHits", [])
                        for opp in opps:
                            grant = Grant(
                                id=_make_id(opp.get("title", ""), opp.get("agency", "")),
                                name=opp.get("title", "Unknown"),
                                funder=opp.get("agency", "Federal"),
                                description=opp.get("synopsis", opp.get("description", "")),
                                estimated_value=opp.get("estFund", opp.get("award_ceiling", "Unknown")),
                                deadline=opp.get("closeDate", opp.get("close_date", None)),
                                source_url=f"https://www.grants.gov/search-results-detail/{opp.get('id', opp.get('opportunity_id', ''))}",
                                source="grants_gov",
                                category=_categorize(opp.get("title", "") + " " + opp.get("synopsis", opp.get("description", ""))),
                                raw_data=opp,
                            )
                            grants.append(grant)
        except Exception as e:
            logger.warning(f"Grants.gov search '{keyword}' failed: {e}")

    return grants


async def scrape_web_fallback(client: httpx.AsyncClient) -> List[Grant]:
    """
    Web search fallback for grants that can't be found via direct APIs.
    Uses public search endpoints and aggregator sites.
    """
    grants = []
    search_queries = [
        "rural development funding open 2026",
        "small business technology grants rural communities 2026",
        "workforce training grants youth foster care 2026",
        "digital inclusion grants rural broadband 2026",
        "AI technology innovation grants small business 2026",
        "state economic development grants open applications 2026",
        "USDA rural business grants 2026",
        "corporate foundation grants technology training youth",
        "community development block grants small cities",
    ]

    for query in search_queries:
        try:
            # Use Google Custom Search-like approach via DuckDuckGo lite
            search_url = "https://html.duckduckgo.com/html/"
            params = {"q": query, "kl": "us-en"}
            resp = await client.get(search_url, params=params, timeout=15.0)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.select(".result__body")
                for result in results[:5]:
                    title_el = result.select_one(".result__title a")
                    snippet_el = result.select_one(".result__snippet")
                    if title_el:
                        title = title_el.get_text(strip=True)
                        href = title_el.get("href", "")
                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                        # Filter for grant-related results
                        combined = f"{title} {snippet}".lower()
                        if any(kw in combined for kw in ["grant", "funding", "apply", "application", "award"]):
                            grants.append(Grant(
                                id=_make_id(title, "web_search"),
                                name=title[:120],
                                funder=_extract_funder(title, snippet),
                                description=snippet[:500],
                                estimated_value=_extract_value(snippet),
                                deadline=None,
                                source_url=href,
                                source="web_search",
                                category=_categorize(f"{title} {snippet}"),
                            ))
        except Exception as e:
            logger.warning(f"Web search '{query}' failed: {e}")

    return grants


async def scrape_open_grants(client: httpx.AsyncClient) -> List[Grant]:
    """Scrape OpenGrants.io for open opportunities."""
    grants = []
    try:
        # OpenGrants has a public search
        search_url = "https://opengrants.io/search"
        params = {"q": "rural technology training funding", "status": "open"}
        resp = await client.get(search_url, params=params, timeout=15.0, follow_redirects=True)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("[class*='grant'], [class*='card'], article")
            for card in cards[:15]:
                title_el = card.select_one("h2, h3, h4, a[href*='grant']")
                if title_el:
                    title = title_el.get_text(strip=True)
                    grants.append(Grant(
                        id=_make_id(title, "OpenGrants"),
                        name=title,
                        funder="Various",
                        description=f"OpenGrants listing: {title}",
                        estimated_value="Varies",
                        deadline=None,
                        source_url=search_url,
                        source="open_grants",
                        category=_categorize(title),
                    ))
    except Exception as e:
        logger.warning(f"OpenGrants scrape failed: {e}")
    return grants


def _extract_funder(title: str, snippet: str) -> str:
    """Try to extract funder name from search result."""
    funders = [
        "USDA", "SBA", "NSF", "NIH", "HUD", "EDA", "NTIA",
        "State DED", "Comcast", "AmEx", "Google", "Microsoft",
        "Ford Foundation", "Knight Foundation", "Kauffman",
    ]
    combined = f"{title} {snippet}"
    for funder in funders:
        if funder.lower() in combined.lower():
            return funder
    return "Unknown Funder"


def _extract_value(text: str) -> str:
    """Try to extract grant value from text."""
    import re
    patterns = [
        r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B))?',
        r'(?:up to|awards? (?:up to|of))\s*\$[\d,]+',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return "Unknown"


async def discover_all() -> List[Grant]:
    """Run all discovery sources and return deduplicated grants."""
    all_grants = []
    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
    ) as client:
        tasks = []
        if SOURCES["grants_gov"]["enabled"]:
            tasks.append(("Grants.gov", scrape_grants_gov(client)))
        if SOURCES["web_search"]["enabled"]:
            tasks.append(("Web Search", scrape_web_fallback(client)))
        tasks.append(("OpenGrants", scrape_open_grants(client)))

        results = await asyncio.gather(
            *[t[1] for t in tasks], return_exceptions=True
        )
        for (name, _), result in zip(tasks, results):
            if isinstance(result, list):
                logger.info(f"  {name}: {len(result)} grants found")
                all_grants.extend(result)
            else:
                logger.warning(f"  {name}: FAILED — {result}")

    # Deduplicate by id
    seen = set()
    unique = []
    for g in all_grants:
        if g.id not in seen:
            seen.add(g.id)
            unique.append(g)
    logger.info(f"Discovered {len(unique)} unique grants from {len(tasks)} sources")
    return unique
