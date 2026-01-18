"""
Semantic Scholar Tool für HayMAS

Ermöglicht Zugriff auf wissenschaftliche Paper und Forschung.
200M+ Paper mit AI-Zusammenfassungen - kostenlos und ohne API-Key!
"""

import httpx
from typing import Dict, Any, List, Optional
import asyncio

from .registry import (
    register_tool,
    ResearchTool,
    ToolCategory,
    create_openai_schema,
    create_anthropic_schema
)


async def _semantic_scholar_search_async(
    query: str, 
    limit: int = 10,
    year_from: Optional[int] = None,
    fields_of_study: Optional[List[str]] = None
) -> List[Dict]:
    """Asynchrone Semantic Scholar Suche."""
    
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,year,authors,citationCount,url,venue,openAccessPdf"
    }
    
    # Optionale Filter
    if year_from:
        params["year"] = f"{year_from}-"
    
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)
    
    headers = {
        "User-Agent": "HayMAS/1.0 (Research Tool)"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers, timeout=15.0)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            return []


def semantic_scholar_search(
    query: str,
    max_results: int = 10,
    year_from: Optional[int] = None,
    fields_of_study: Optional[str] = None
) -> Dict[str, Any]:
    """
    Durchsucht Semantic Scholar nach wissenschaftlichen Papern.
    
    Args:
        query: Suchbegriff (englisch empfohlen für beste Ergebnisse)
        max_results: Maximale Anzahl Ergebnisse (1-20)
        year_from: Optional - nur Paper ab diesem Jahr
        fields_of_study: Optional - Fachbereich z.B. "Computer Science"
    
    Returns:
        Dict mit Suchergebnissen
    """
    
    async def _search():
        try:
            # Fields of Study parsen wenn angegeben
            fos_list = None
            if fields_of_study:
                fos_list = [f.strip() for f in fields_of_study.split(",")]
            
            papers = await _semantic_scholar_search_async(
                query=query,
                limit=min(max_results, 20),
                year_from=year_from,
                fields_of_study=fos_list
            )
            
            results = []
            for paper in papers:
                # Autoren formatieren
                authors = paper.get("authors", [])
                author_names = ", ".join([a.get("name", "") for a in authors[:3]])
                if len(authors) > 3:
                    author_names += f" et al. ({len(authors)} authors)"
                
                # URL bestimmen (bevorzugt Open Access PDF)
                url = paper.get("url", "")
                open_access = paper.get("openAccessPdf")
                if open_access and open_access.get("url"):
                    pdf_url = open_access["url"]
                else:
                    pdf_url = None
                
                # Abstract kürzen
                abstract = paper.get("abstract", "") or ""
                if len(abstract) > 500:
                    abstract = abstract[:497] + "..."
                
                results.append({
                    "title": paper.get("title", ""),
                    "url": url,
                    "pdf_url": pdf_url,
                    "snippet": abstract,
                    "year": paper.get("year"),
                    "authors": author_names,
                    "citations": paper.get("citationCount", 0),
                    "venue": paper.get("venue", "")
                })
            
            return {
                "success": True,
                "tool": "semantic_scholar",
                "query": query,
                "results": results,
                "result_count": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "tool": "semantic_scholar",
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

_SEMANTIC_SCHOLAR_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff (Englisch empfohlen für wissenschaftliche Paper)"
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-20)",
            "default": 10
        },
        "year_from": {
            "type": "integer",
            "description": "Optional: Nur Paper ab diesem Jahr (z.B. 2020)"
        },
        "fields_of_study": {
            "type": "string",
            "description": "Optional: Fachbereich z.B. 'Computer Science' oder 'Medicine'"
        }
    },
    "required": ["query"]
}

_SEMANTIC_SCHOLAR_DESCRIPTION = """Durchsucht Semantic Scholar nach wissenschaftlichen Papern und Forschungsarbeiten. 
Ideal für: akademische Forschung, wissenschaftliche Fakten, Studien, Meta-Analysen, State-of-the-Art in Fachgebieten.
Enthält 200M+ Paper mit Abstracts, Autoren und Zitationen."""

SEMANTIC_SCHOLAR_TOOL = create_openai_schema(
    name="semantic_scholar_search",
    description=_SEMANTIC_SCHOLAR_DESCRIPTION,
    parameters=_SEMANTIC_SCHOLAR_PARAMETERS
)

SEMANTIC_SCHOLAR_TOOL_ANTHROPIC = create_anthropic_schema(
    name="semantic_scholar_search",
    description=_SEMANTIC_SCHOLAR_DESCRIPTION,
    parameters=_SEMANTIC_SCHOLAR_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="semantic_scholar",
    name="Semantic Scholar",
    description="Wissenschaftliche Paper und Forschungsarbeiten (200M+ Papers)",
    category=ToolCategory.SCIENCE,
    best_for=["wissenschaft", "forschung", "studien", "akademische quellen", "state-of-the-art", "paper"],
    topic_types=["science", "tech", "medicine", "academic"],
    icon="🎓",
    is_free=True,
    search_func=semantic_scholar_search,
    requires_api_key=False,
    tool_schema_openai=SEMANTIC_SCHOLAR_TOOL,
    tool_schema_anthropic=SEMANTIC_SCHOLAR_TOOL_ANTHROPIC
))
