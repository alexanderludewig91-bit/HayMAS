"""
Hacker News Tool für HayMAS

Ermöglicht Zugriff auf Tech-Diskussionen der Hacker News Community.
Nutzt die offizielle Algolia API - kostenlos und ohne API-Key.
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


async def _hackernews_search_async(
    query: str, 
    limit: int = 10,
    sort_by: str = "relevance"
) -> List[Dict]:
    """Asynchrone Hacker News Suche via Algolia API."""
    
    # Algolia HN Search API
    if sort_by == "date":
        url = "https://hn.algolia.com/api/v1/search_by_date"
    else:
        url = "https://hn.algolia.com/api/v1/search"
    
    params = {
        "query": query,
        "hitsPerPage": limit,
        "tags": "(story,poll)"  # Nur Stories und Polls, keine Kommentare
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        data = response.json()
        return data.get("hits", [])


def hackernews_search(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    min_points: int = 0
) -> Dict[str, Any]:
    """
    Durchsucht Hacker News nach Tech-Diskussionen.
    
    Args:
        query: Suchbegriff
        max_results: Maximale Anzahl Ergebnisse (1-30)
        sort_by: "relevance" oder "date"
        min_points: Mindestanzahl Upvotes (0 = alle)
    
    Returns:
        Dict mit Suchergebnissen
    """
    import asyncio
    
    async def _search():
        try:
            hits = await _hackernews_search_async(
                query=query,
                limit=min(max_results, 30),
                sort_by=sort_by
            )
            
            results = []
            for hit in hits:
                points = hit.get("points", 0) or 0
                
                # Filter nach Mindestpunkten
                if points < min_points:
                    continue
                
                # URL: Entweder externer Link oder HN-Diskussion
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                
                results.append({
                    "title": hit.get("title", ""),
                    "url": url,
                    "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "snippet": hit.get("story_text", "")[:300] if hit.get("story_text") else "",
                    "points": points,
                    "comments": hit.get("num_comments", 0) or 0,
                    "author": hit.get("author", ""),
                    "created_at": hit.get("created_at", "")
                })
            
            return {
                "success": True,
                "tool": "hackernews",
                "query": query,
                "sort_by": sort_by,
                "results": results,
                "result_count": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "tool": "hackernews",
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

_HACKERNEWS_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff (Englisch empfohlen für bessere Ergebnisse)"
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-30)",
            "default": 10
        },
        "sort_by": {
            "type": "string",
            "enum": ["relevance", "date"],
            "description": "Sortierung: 'relevance' für beste Treffer, 'date' für neueste",
            "default": "relevance"
        },
        "min_points": {
            "type": "integer",
            "description": "Mindestanzahl Upvotes (0 = alle Ergebnisse)",
            "default": 0
        }
    },
    "required": ["query"]
}

_HACKERNEWS_DESCRIPTION = "Durchsucht Hacker News nach Tech-Diskussionen, Meinungen und Erfahrungen der Developer-Community. Ideal für technische Bewertungen, Tool-Vergleiche und Community-Perspektiven."

HACKERNEWS_SEARCH_TOOL = create_openai_schema(
    name="hackernews_search",
    description=_HACKERNEWS_DESCRIPTION,
    parameters=_HACKERNEWS_PARAMETERS
)

HACKERNEWS_SEARCH_TOOL_ANTHROPIC = create_anthropic_schema(
    name="hackernews_search",
    description=_HACKERNEWS_DESCRIPTION,
    parameters=_HACKERNEWS_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="hackernews",
    name="Hacker News",
    description="Tech-Diskussionen der Developer-Community",
    category=ToolCategory.TECH_COMMUNITY,
    best_for=["tech-meinungen", "tool-vergleiche", "developer-perspektiven", "startup-news", "open-source"],
    topic_types=["tech", "programming", "startups", "ai"],
    icon="🔶",
    is_free=True,
    search_func=hackernews_search,
    requires_api_key=False,
    tool_schema_openai=HACKERNEWS_SEARCH_TOOL,
    tool_schema_anthropic=HACKERNEWS_SEARCH_TOOL_ANTHROPIC
))
