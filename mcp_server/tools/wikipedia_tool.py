"""
Wikipedia Tool für HayMAS

Ermöglicht Zugriff auf enzyklopädisches Grundlagenwissen.
Kostenlos und ohne API-Key nutzbar.
"""

import httpx
from typing import Dict, Any, List, Optional

from .registry import (
    register_tool,
    ResearchTool,
    ToolCategory,
    create_openai_schema,
    create_anthropic_schema
)


async def _wikipedia_search_async(query: str, limit: int = 5, language: str = "de") -> List[Dict]:
    """Asynchrone Wikipedia-Suche."""
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
        "utf8": 1
    }
    
    # Wikipedia erfordert einen User-Agent
    headers = {
        "User-Agent": "HayMAS/1.0 (Research Tool; https://github.com/haymas)"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers, timeout=10.0)
        data = response.json()
        return data.get("query", {}).get("search", [])


async def _wikipedia_summary_async(title: str, language: str = "de") -> Dict:
    """Holt die Zusammenfassung eines Wikipedia-Artikels."""
    # URL-encode des Titels
    import urllib.parse
    encoded_title = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
    
    headers = {
        "User-Agent": "HayMAS/1.0 (Research Tool; https://github.com/haymas)"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        return {}


def wikipedia_search(
    query: str,
    max_results: int = 5,
    language: str = "de",
    include_summaries: bool = True
) -> Dict[str, Any]:
    """
    Durchsucht Wikipedia nach relevanten Artikeln.
    
    Args:
        query: Suchbegriff
        max_results: Maximale Anzahl Ergebnisse (1-10)
        language: Sprachcode ("de", "en")
        include_summaries: Ob Zusammenfassungen geladen werden sollen
    
    Returns:
        Dict mit Suchergebnissen
    """
    import asyncio
    
    async def _search():
        try:
            # Suche durchführen
            search_results = await _wikipedia_search_async(query, max_results, language)
            
            results = []
            for item in search_results:
                title = item.get("title", "")
                page_id = item.get("pageid", "")
                snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                
                result = {
                    "title": title,
                    "url": f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "snippet": snippet,
                    "page_id": page_id
                }
                
                # Optional: Zusammenfassung laden
                if include_summaries:
                    summary_data = await _wikipedia_summary_async(title, language)
                    if summary_data:
                        result["summary"] = summary_data.get("extract", "")[:500]
                        if summary_data.get("thumbnail"):
                            result["thumbnail"] = summary_data["thumbnail"].get("source", "")
                
                results.append(result)
            
            return {
                "success": True,
                "tool": "wikipedia",
                "query": query,
                "language": language,
                "results": results,
                "result_count": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "tool": "wikipedia",
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

_WIKIPEDIA_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff. Nutze klare, präzise Begriffe."
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-10)",
            "default": 5
        },
        "language": {
            "type": "string",
            "enum": ["de", "en"],
            "description": "Sprache: 'de' für Deutsch, 'en' für Englisch",
            "default": "de"
        }
    },
    "required": ["query"]
}

_WIKIPEDIA_DESCRIPTION = "Durchsucht Wikipedia nach enzyklopädischem Grundlagenwissen. Ideal für Definitionen, Konzepte, historische Fakten und etabliertes Wissen."

WIKIPEDIA_SEARCH_TOOL = create_openai_schema(
    name="wikipedia_search",
    description=_WIKIPEDIA_DESCRIPTION,
    parameters=_WIKIPEDIA_PARAMETERS
)

WIKIPEDIA_SEARCH_TOOL_ANTHROPIC = create_anthropic_schema(
    name="wikipedia_search",
    description=_WIKIPEDIA_DESCRIPTION,
    parameters=_WIKIPEDIA_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="wikipedia",
    name="Wikipedia",
    description="Enzyklopädisches Grundlagenwissen",
    category=ToolCategory.KNOWLEDGE,
    best_for=["grundlagen", "definitionen", "konzepte", "historische fakten", "etabliertes wissen"],
    topic_types=["general", "science", "history", "tech", "culture"],
    icon="📚",
    is_free=True,
    search_func=wikipedia_search,
    requires_api_key=False,
    tool_schema_openai=WIKIPEDIA_SEARCH_TOOL,
    tool_schema_anthropic=WIKIPEDIA_SEARCH_TOOL_ANTHROPIC
))
