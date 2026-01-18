"""
arXiv Tool für HayMAS

Ermöglicht Zugriff auf wissenschaftliche Preprints.
Besonders stark in: Machine Learning, KI, Physik, Mathematik, Computer Science.
Kostenlos und ohne API-Key!
"""

import httpx
from typing import Dict, Any, List, Optional
import asyncio
import re
from xml.etree import ElementTree

from .registry import (
    register_tool,
    ResearchTool,
    ToolCategory,
    create_openai_schema,
    create_anthropic_schema
)


async def _arxiv_search_async(
    query: str, 
    max_results: int = 10,
    sort_by: str = "relevance"
) -> List[Dict]:
    """Asynchrone arXiv Suche via Atom API."""
    
    # arXiv API URL
    url = "http://export.arxiv.org/api/query"
    
    # Sort-Parameter
    sort_map = {
        "relevance": "relevance",
        "date": "submittedDate",
        "citations": "relevance"  # arXiv hat keine Citation-Sortierung
    }
    
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_map.get(sort_by, "relevance"),
        "sortOrder": "descending"
    }
    
    headers = {
        "User-Agent": "HayMAS/1.0 (Research Tool)"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers, timeout=15.0)
        
        if response.status_code == 200:
            return _parse_arxiv_response(response.text)
        else:
            return []


def _parse_arxiv_response(xml_text: str) -> List[Dict]:
    """Parst die arXiv Atom XML Response."""
    
    results = []
    
    # Namespace für Atom
    namespaces = {
        'atom': 'http://www.w3.org/2005/Atom',
        'arxiv': 'http://arxiv.org/schemas/atom'
    }
    
    try:
        root = ElementTree.fromstring(xml_text)
        
        for entry in root.findall('atom:entry', namespaces):
            # ID (arXiv ID)
            id_elem = entry.find('atom:id', namespaces)
            arxiv_url = id_elem.text if id_elem is not None else ""
            arxiv_id = arxiv_url.split('/')[-1] if arxiv_url else ""
            
            # Titel
            title_elem = entry.find('atom:title', namespaces)
            title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else ""
            
            # Abstract
            summary_elem = entry.find('atom:summary', namespaces)
            abstract = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else ""
            if len(abstract) > 500:
                abstract = abstract[:497] + "..."
            
            # Autoren
            authors = []
            for author in entry.findall('atom:author', namespaces):
                name_elem = author.find('atom:name', namespaces)
                if name_elem is not None:
                    authors.append(name_elem.text)
            
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += f" et al. ({len(authors)} authors)"
            
            # Datum
            published_elem = entry.find('atom:published', namespaces)
            published = published_elem.text[:10] if published_elem is not None else ""
            
            # Kategorien
            categories = []
            for cat in entry.findall('atom:category', namespaces):
                term = cat.get('term', '')
                if term:
                    categories.append(term)
            
            # PDF Link
            pdf_url = ""
            for link in entry.findall('atom:link', namespaces):
                if link.get('title') == 'pdf':
                    pdf_url = link.get('href', '')
                    break
            
            if not pdf_url and arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            results.append({
                "title": title,
                "url": arxiv_url,
                "pdf_url": pdf_url,
                "snippet": abstract,
                "authors": author_str,
                "published": published,
                "arxiv_id": arxiv_id,
                "categories": categories[:3]  # Max 3 Kategorien
            })
            
    except ElementTree.ParseError:
        pass
    
    return results


def arxiv_search(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance"
) -> Dict[str, Any]:
    """
    Durchsucht arXiv nach wissenschaftlichen Preprints.
    
    Args:
        query: Suchbegriff (Englisch empfohlen)
        max_results: Maximale Anzahl Ergebnisse (1-20)
        sort_by: "relevance" oder "date"
    
    Returns:
        Dict mit Suchergebnissen
    """
    
    async def _search():
        try:
            papers = await _arxiv_search_async(
                query=query,
                max_results=min(max_results, 20),
                sort_by=sort_by
            )
            
            results = [
                {
                    "title": p["title"],
                    "url": p["url"],
                    "pdf_url": p["pdf_url"],
                    "snippet": p["snippet"],
                    "authors": p["authors"],
                    "published": p["published"],
                    "arxiv_id": p["arxiv_id"],
                    "categories": p["categories"]
                }
                for p in papers
            ]
            
            return {
                "success": True,
                "tool": "arxiv",
                "query": query,
                "results": results,
                "result_count": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "tool": "arxiv",
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

_ARXIV_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Der Suchbegriff (Englisch für beste Ergebnisse). Kann Fachbegriffe, Autorennamen oder arXiv IDs enthalten."
        },
        "max_results": {
            "type": "integer",
            "description": "Anzahl gewünschter Ergebnisse (1-20)",
            "default": 10
        },
        "sort_by": {
            "type": "string",
            "enum": ["relevance", "date"],
            "description": "Sortierung: 'relevance' für beste Treffer, 'date' für neueste",
            "default": "relevance"
        }
    },
    "required": ["query"]
}

_ARXIV_DESCRIPTION = """Durchsucht arXiv nach wissenschaftlichen Preprints und Papers.
Besonders stark in: Machine Learning, KI, Computer Science, Physik, Mathematik.
Enthält neueste Forschung oft vor der offiziellen Publikation."""

ARXIV_TOOL = create_openai_schema(
    name="arxiv_search",
    description=_ARXIV_DESCRIPTION,
    parameters=_ARXIV_PARAMETERS
)

ARXIV_TOOL_ANTHROPIC = create_anthropic_schema(
    name="arxiv_search",
    description=_ARXIV_DESCRIPTION,
    parameters=_ARXIV_PARAMETERS
)


# =============================================================================
# TOOL IN REGISTRY REGISTRIEREN
# =============================================================================

register_tool(ResearchTool(
    id="arxiv",
    name="arXiv",
    description="Wissenschaftliche Preprints (ML, KI, Physik, Math, CS)",
    category=ToolCategory.SCIENCE,
    best_for=["preprints", "machine learning", "ki forschung", "computer science", "physik", "mathematik"],
    topic_types=["science", "tech", "ai", "academic"],
    icon="📄",
    is_free=True,
    search_func=arxiv_search,
    requires_api_key=False,
    tool_schema_openai=ARXIV_TOOL,
    tool_schema_anthropic=ARXIV_TOOL_ANTHROPIC
))
