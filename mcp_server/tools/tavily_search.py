"""
Tavily Web-Suche Tool für HayMAS

Ermöglicht Agenten, aktuelle Informationen aus dem Web zu recherchieren.
"""

import os
from typing import List, Dict, Any, Optional

from .registry import (
    register_tool, 
    ResearchTool, 
    ToolCategory,
    create_openai_schema,
    create_anthropic_schema
)

# Tavily wird lazy importiert um Fehler bei fehlendem Key zu vermeiden
_tavily_client = None


def _get_tavily_client():
    """Lazy initialization des Tavily Clients"""
    global _tavily_client
    if _tavily_client is None:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            raise ValueError("TAVILY_API_KEY nicht gesetzt. Bitte in .env konfigurieren.")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Führt eine Web-Suche mit Tavily durch.
    
    Args:
        query: Suchbegriff/Frage
        max_results: Maximale Anzahl Ergebnisse (1-10)
        search_depth: "basic" oder "advanced" (advanced = mehr Kontext)
        include_domains: Optional - nur diese Domains durchsuchen
        exclude_domains: Optional - diese Domains ausschließen
    
    Returns:
        Dict mit:
        - success: bool
        - results: Liste von Suchergebnissen
        - query: Ursprüngliche Anfrage
        - error: Optional - Fehlermeldung bei Problemen
    """
    try:
        client = _get_tavily_client()
        
        # Tavily API aufrufen
        response = client.search(
            query=query,
            max_results=min(max_results, 10),
            search_depth=search_depth,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or []
        )
        
        # Ergebnisse formatieren
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0.0)
            })
        
        return {
            "success": True,
            "tool": "tavily",
            "query": query,
            "results": results,
            "result_count": len(results)
        }
        
    except Exception as e:
        return {
            "success": False,
            "tool": "tavily",
            "query": query,
            "results": [],
            "result_count": 0,
            "error": str(e)
        }


# =============================================================================
# TOOL-SCHEMA DEFINITIONEN
# =============================================================================

_TAVILY_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff oder die Frage. Formuliere präzise für bessere Ergebnisse."
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-10)",
            "default": 5
        },
        "search_depth": {
            "type": "string",
            "enum": ["basic", "advanced"],
            "description": "basic = schnell, advanced = mehr Kontext",
            "default": "basic"
        }
    },
    "required": ["query"]
}

_TAVILY_DESCRIPTION = "Durchsucht das Web nach aktuellen Informationen zu einem Thema. Nutze dies für Recherche zu Fakten, Trends, technischen Details etc."

# Tool-Definition für LLM Function Calling (OpenAI Format)
TAVILY_SEARCH_TOOL = create_openai_schema(
    name="tavily_search",
    description=_TAVILY_DESCRIPTION,
    parameters=_TAVILY_PARAMETERS
)

# Anthropic Tool-Format
TAVILY_SEARCH_TOOL_ANTHROPIC = create_anthropic_schema(
    name="tavily_search",
    description=_TAVILY_DESCRIPTION,
    parameters=_TAVILY_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="tavily",
    name="Tavily Web Search",
    description="KI-optimierte Websuche mit guten Snippets",
    category=ToolCategory.WEB_SEARCH,
    best_for=["aktuelle informationen", "fakten", "trends", "technische details"],
    topic_types=["general", "tech", "business", "science", "current_events"],
    icon="🌐",
    is_free=False,
    search_func=tavily_search,
    requires_api_key=True,
    api_key_env_var="TAVILY_API_KEY",
    tool_schema_openai=TAVILY_SEARCH_TOOL,
    tool_schema_anthropic=TAVILY_SEARCH_TOOL_ANTHROPIC
))
