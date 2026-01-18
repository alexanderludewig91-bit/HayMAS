"""
Google News Tool für HayMAS

Ermöglicht Zugriff auf aktuelle Nachrichten via gnews Library.
Kostenlos und ohne API-Key nutzbar.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .registry import (
    register_tool,
    ResearchTool,
    ToolCategory,
    create_openai_schema,
    create_anthropic_schema
)

# gnews wird lazy importiert
_gnews_client = None


def _get_gnews_client(language: str = "de", country: str = "DE", period: str = "7d"):
    """Lazy initialization des GNews Clients"""
    global _gnews_client
    try:
        from gnews import GNews
        _gnews_client = GNews(
            language=language,
            country=country,
            period=period,
            max_results=10
        )
        return _gnews_client
    except ImportError:
        raise ImportError("gnews nicht installiert. Bitte 'pip install gnews' ausführen.")


def gnews_search(
    query: str,
    max_results: int = 10,
    period: str = "7d",
    language: str = "de",
    country: str = "DE"
) -> Dict[str, Any]:
    """
    Durchsucht Google News nach aktuellen Nachrichten.
    
    Args:
        query: Suchbegriff
        max_results: Maximale Anzahl Ergebnisse (1-20)
        period: Zeitraum - "1d", "7d", "30d", "1y"
        language: Sprache ("de", "en")
        country: Land ("DE", "US", "AT", "CH")
    
    Returns:
        Dict mit Suchergebnissen
    """
    try:
        from gnews import GNews
        
        # Neuen Client für diese Anfrage erstellen (wegen Parametern)
        gnews = GNews(
            language=language,
            country=country,
            period=period,
            max_results=min(max_results, 20)
        )
        
        # Suche durchführen
        raw_results = gnews.get_news(query)
        
        results = []
        for item in raw_results or []:
            # Datum parsen
            published = item.get("published date", "")
            
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "published": published,
                "source": item.get("publisher", {}).get("title", "Unbekannt")
            })
        
        return {
            "success": True,
            "tool": "gnews",
            "query": query,
            "period": period,
            "results": results,
            "result_count": len(results)
        }
        
    except ImportError:
        return {
            "success": False,
            "tool": "gnews",
            "query": query,
            "results": [],
            "result_count": 0,
            "error": "gnews nicht installiert. Bitte 'pip install gnews' ausführen."
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "gnews",
            "query": query,
            "results": [],
            "result_count": 0,
            "error": str(e)
        }


# =============================================================================
# TOOL-SCHEMA DEFINITIONEN
# =============================================================================

_GNEWS_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff für Nachrichten"
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-20)",
            "default": 10
        },
        "period": {
            "type": "string",
            "enum": ["1d", "7d", "30d", "1y"],
            "description": "Zeitraum: 1d=heute, 7d=letzte Woche, 30d=letzter Monat, 1y=letztes Jahr",
            "default": "7d"
        },
        "language": {
            "type": "string",
            "enum": ["de", "en"],
            "description": "Sprache der Nachrichten",
            "default": "de"
        }
    },
    "required": ["query"]
}

_GNEWS_DESCRIPTION = "Durchsucht Google News nach aktuellen Nachrichten und Pressemeldungen. Ideal für aktuelle Ereignisse, Trends und Entwicklungen."

GNEWS_SEARCH_TOOL = create_openai_schema(
    name="gnews_search",
    description=_GNEWS_DESCRIPTION,
    parameters=_GNEWS_PARAMETERS
)

GNEWS_SEARCH_TOOL_ANTHROPIC = create_anthropic_schema(
    name="gnews_search",
    description=_GNEWS_DESCRIPTION,
    parameters=_GNEWS_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="gnews",
    name="Google News",
    description="Aktuelle Nachrichten und Pressemeldungen",
    category=ToolCategory.NEWS,
    best_for=["aktuelle nachrichten", "pressemeldungen", "trends", "ereignisse", "entwicklungen"],
    topic_types=["current_events", "business", "tech", "politics", "general"],
    icon="📰",
    is_free=True,
    search_func=gnews_search,
    requires_api_key=False,
    tool_schema_openai=GNEWS_SEARCH_TOOL,
    tool_schema_anthropic=GNEWS_SEARCH_TOOL_ANTHROPIC
))
