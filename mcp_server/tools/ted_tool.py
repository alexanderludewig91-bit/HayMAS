"""
TED (Tenders Electronic Daily) Tool für HayMAS

Ermöglicht Zugriff auf EU-Ausschreibungen und öffentliche Vergaben.
Perfekt für: Öffentliche Verwaltung, IT-Beschaffung, Government.
Kostenlos und ohne API-Key!
"""

import httpx
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta

from .registry import (
    register_tool,
    ResearchTool,
    ToolCategory,
    create_openai_schema,
    create_anthropic_schema
)


async def _ted_search_async(
    query: str, 
    max_results: int = 10,
    country: Optional[str] = None,
    days_back: int = 365
) -> List[Dict]:
    """
    Asynchrone TED Suche via EU Open Data Portal.
    
    TED API ist komplex, daher nutzen wir den einfacheren EU Open Data Ansatz
    oder die TED Website Search API.
    """
    
    # TED Search API (vereinfacht)
    # Offizielle API: https://ted.europa.eu/api/
    url = "https://ted.europa.eu/api/v3.0/notices/search"
    
    # Datum berechnen
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    
    # Query aufbauen
    search_params = {
        "q": query,
        "pageSize": min(max_results, 20),
        "pageNum": 1,
        "scope": 3,  # Alle Dokumente
        "sortField": "PD",  # Publication Date
        "sortOrder": "desc"
    }
    
    # Land-Filter
    if country:
        search_params["country"] = country.upper()
    
    headers = {
        "User-Agent": "HayMAS/1.0 (Research Tool)",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                params=search_params, 
                headers=headers, 
                timeout=15.0,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                data = response.json()
                return _parse_ted_response(data)
            else:
                # Fallback: Einfache Suche über TED Website
                return await _ted_website_search(query, max_results, country)
    except Exception:
        # Fallback bei API-Problemen
        return await _ted_website_search(query, max_results, country)


async def _ted_website_search(
    query: str,
    max_results: int = 10,
    country: Optional[str] = None
) -> List[Dict]:
    """
    Fallback: Suche über TED Website RSS/Atom Feed.
    """
    
    # TED RSS Feed für Suche
    base_url = "https://ted.europa.eu/api/v2.0/notices/search"
    
    params = {
        "q": query,
        "pageSize": min(max_results, 20),
        "pageNum": 1,
    }
    
    if country:
        params["country"] = country.upper()
    
    headers = {
        "User-Agent": "HayMAS/1.0 (Research Tool)",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                params=params,
                headers=headers,
                timeout=15.0,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return _parse_ted_response(data)
                except:
                    pass
    except:
        pass
    
    # Wenn alles fehlschlägt, leere Liste
    return []


def _parse_ted_response(data: Dict) -> List[Dict]:
    """Parst die TED API Response."""
    
    results = []
    
    # Verschiedene Response-Formate unterstützen
    notices = data.get("notices", data.get("results", data.get("data", [])))
    
    if not isinstance(notices, list):
        notices = []
    
    for notice in notices:
        try:
            # TED Notice ID
            notice_id = notice.get("noticeId", notice.get("id", notice.get("docId", "")))
            
            # Titel
            title = notice.get("title", notice.get("titleText", ""))
            if isinstance(title, dict):
                title = title.get("value", title.get("text", str(title)))
            
            # Beschreibung
            description = notice.get("description", notice.get("shortDescription", ""))
            if isinstance(description, dict):
                description = description.get("value", description.get("text", str(description)))
            if len(description) > 400:
                description = description[:397] + "..."
            
            # URL
            url = notice.get("links", {}).get("html", "")
            if not url and notice_id:
                url = f"https://ted.europa.eu/notice/{notice_id}"
            
            # Auftraggeber
            buyer = notice.get("buyer", notice.get("contractingAuthority", {}))
            if isinstance(buyer, dict):
                buyer_name = buyer.get("name", buyer.get("officialName", ""))
            else:
                buyer_name = str(buyer) if buyer else ""
            
            # Land
            country = notice.get("country", notice.get("countryCode", ""))
            if isinstance(country, dict):
                country = country.get("code", country.get("value", ""))
            
            # Datum
            pub_date = notice.get("publicationDate", notice.get("datePublished", ""))
            
            # Wert
            value = notice.get("estimatedValue", notice.get("value", {}))
            if isinstance(value, dict):
                amount = value.get("amount", value.get("value", ""))
                currency = value.get("currency", "EUR")
                value_str = f"{amount} {currency}" if amount else ""
            else:
                value_str = str(value) if value else ""
            
            # CPV Codes (Klassifizierung)
            cpv = notice.get("cpvCodes", notice.get("cpv", []))
            if isinstance(cpv, list) and cpv:
                cpv_str = ", ".join([str(c.get("code", c)) if isinstance(c, dict) else str(c) for c in cpv[:3]])
            else:
                cpv_str = ""
            
            results.append({
                "title": title,
                "url": url,
                "snippet": description,
                "notice_id": notice_id,
                "buyer": buyer_name,
                "country": country,
                "published": pub_date,
                "value": value_str,
                "cpv_codes": cpv_str
            })
            
        except Exception:
            continue
    
    return results


def ted_search(
    query: str,
    max_results: int = 10,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Durchsucht TED (Tenders Electronic Daily) nach EU-Ausschreibungen.
    
    Args:
        query: Suchbegriff (z.B. "Low-Code Platform", "IT-System")
        max_results: Maximale Anzahl Ergebnisse (1-20)
        country: Optional - Ländercode (DE, AT, FR, etc.)
    
    Returns:
        Dict mit Suchergebnissen
    """
    
    async def _search():
        try:
            notices = await _ted_search_async(
                query=query,
                max_results=min(max_results, 20),
                country=country
            )
            
            return {
                "success": True,
                "tool": "ted",
                "query": query,
                "country_filter": country,
                "results": notices,
                "result_count": len(notices)
            }
            
        except Exception as e:
            return {
                "success": False,
                "tool": "ted",
                "query": query,
                "results": [],
                "result_count": 0,
                "error": str(e)
            }
    
    # Async in sync wrapper
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_search())


# =============================================================================
# TOOL-SCHEMA DEFINITIONEN
# =============================================================================

_TED_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff für Ausschreibungen (z.B. 'Low-Code Platform', 'IT-System', 'Software')"
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-20)",
            "default": 10
        },
        "country": {
            "type": "string",
            "description": "Optional: Ländercode für Filter (DE, AT, FR, etc.)"
        }
    },
    "required": ["query"]
}

_TED_DESCRIPTION = """Durchsucht TED (Tenders Electronic Daily) nach EU-Ausschreibungen und öffentlichen Vergaben.
Ideal für: IT-Beschaffungen der öffentlichen Verwaltung, Behörden-Projekte, Government IT.
Enthält Ausschreibungen aller EU-Länder mit Auftraggeber, Wert und Details."""

TED_TOOL = create_openai_schema(
    name="ted_search",
    description=_TED_DESCRIPTION,
    parameters=_TED_PARAMETERS
)

TED_TOOL_ANTHROPIC = create_anthropic_schema(
    name="ted_search",
    description=_TED_DESCRIPTION,
    parameters=_TED_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="ted",
    name="TED EU-Ausschreibungen",
    description="EU-Ausschreibungen und öffentliche Vergaben",
    category=ToolCategory.BUSINESS,
    best_for=["ausschreibungen", "öffentliche vergabe", "it-beschaffung", "government", "behörden", "verwaltung"],
    topic_types=["business", "government", "public_sector", "tech"],
    icon="🏛️",
    is_free=True,
    search_func=ted_search,
    requires_api_key=False,
    tool_schema_openai=TED_TOOL,
    tool_schema_anthropic=TED_TOOL_ANTHROPIC
))
