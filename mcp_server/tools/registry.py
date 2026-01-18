"""
HayMAS Tool Registry

Zentrale Verwaltung aller Research-Tools.
Neue Tools können einfach registriert werden, ohne den Orchestrator anzupassen.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from enum import Enum


class ToolCategory(Enum):
    """Kategorien für Research-Tools"""
    WEB_SEARCH = "web_search"       # Allgemeine Websuche
    NEWS = "news"                    # Aktuelle Nachrichten
    SCIENCE = "science"              # Wissenschaftliche Paper
    BUSINESS = "business"            # Unternehmensdaten
    KNOWLEDGE = "knowledge"          # Enzyklopädisches Wissen
    TECH_COMMUNITY = "tech_community" # Tech-Diskussionen
    STATISTICS = "statistics"        # Statistiken & Daten


@dataclass
class ResearchTool:
    """Definition eines Research-Tools für die Registry"""
    
    # Identifikation
    id: str                          # Eindeutige ID: "tavily", "wikipedia", etc.
    name: str                        # Anzeigename: "Tavily Web Search"
    description: str                 # Kurzbeschreibung für UI
    
    # Kategorisierung (für Orchestrator-Routing)
    category: ToolCategory
    best_for: List[str]              # ["grundlagen", "definitionen", "aktuelle news"]
    topic_types: List[str]           # ["tech", "science", "business", "general"]
    
    # UI-Darstellung
    icon: str = "🔍"
    is_free: bool = True
    
    # Technisch
    search_func: Optional[Callable] = None  # Die eigentliche Suchfunktion
    requires_api_key: bool = False
    api_key_env_var: Optional[str] = None
    
    # LLM Tool-Definition (wird automatisch generiert)
    tool_schema_openai: Dict = field(default_factory=dict)
    tool_schema_anthropic: Dict = field(default_factory=dict)


# =============================================================================
# GLOBALE TOOL REGISTRY
# =============================================================================

_TOOL_REGISTRY: Dict[str, ResearchTool] = {}


def register_tool(tool: ResearchTool) -> None:
    """
    Registriert ein neues Research-Tool.
    
    Args:
        tool: ResearchTool-Instanz
    """
    _TOOL_REGISTRY[tool.id] = tool


def get_tool(tool_id: str) -> Optional[ResearchTool]:
    """
    Gibt ein Tool nach ID zurück.
    
    Args:
        tool_id: Tool-ID (z.B. "tavily")
    
    Returns:
        ResearchTool oder None
    """
    return _TOOL_REGISTRY.get(tool_id)


def get_all_tools() -> List[ResearchTool]:
    """Gibt alle registrierten Tools zurück."""
    return list(_TOOL_REGISTRY.values())


def get_tools_by_category(category: ToolCategory) -> List[ResearchTool]:
    """Gibt alle Tools einer Kategorie zurück."""
    return [t for t in _TOOL_REGISTRY.values() if t.category == category]


def get_tools_for_topic(topic_type: str) -> List[ResearchTool]:
    """
    Gibt passende Tools für einen Thementyp zurück.
    
    Args:
        topic_type: z.B. "tech", "science", "business"
    
    Returns:
        Liste passender Tools, sortiert nach Relevanz
    """
    matching = [t for t in _TOOL_REGISTRY.values() if topic_type in t.topic_types]
    # Immer auch "general" Tools einschließen
    general = [t for t in _TOOL_REGISTRY.values() if "general" in t.topic_types and t not in matching]
    return matching + general


def get_free_tools() -> List[ResearchTool]:
    """Gibt alle kostenlosen Tools zurück."""
    return [t for t in _TOOL_REGISTRY.values() if t.is_free]


def get_tools_description_for_prompt() -> str:
    """
    Generiert eine Beschreibung aller Tools für LLM-Prompts.
    
    Returns:
        Formatierte Tool-Beschreibung
    """
    lines = []
    for tool in _TOOL_REGISTRY.values():
        cost = "kostenlos" if tool.is_free else "kostenpflichtig"
        lines.append(
            f"- **{tool.id}** ({tool.icon} {tool.name}): {tool.description}\n"
            f"  Gut für: {', '.join(tool.best_for)} | {cost}"
        )
    return "\n".join(lines)


def get_tools_for_api() -> List[Dict[str, Any]]:
    """
    Gibt Tool-Informationen für die API zurück (für Frontend).
    
    Returns:
        Liste von Tool-Dicts
    """
    return [
        {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "category": tool.category.value,
            "icon": tool.icon,
            "is_free": tool.is_free,
            "best_for": tool.best_for,
            "topic_types": tool.topic_types,
        }
        for tool in _TOOL_REGISTRY.values()
    ]


def execute_tool(tool_id: str, **kwargs) -> Dict[str, Any]:
    """
    Führt ein Tool aus.
    
    Args:
        tool_id: Tool-ID
        **kwargs: Tool-spezifische Parameter
    
    Returns:
        Tool-Ergebnis als Dict
    """
    tool = get_tool(tool_id)
    if not tool:
        return {
            "success": False,
            "error": f"Tool '{tool_id}' nicht gefunden",
            "results": []
        }
    
    if not tool.search_func:
        return {
            "success": False,
            "error": f"Tool '{tool_id}' hat keine Suchfunktion",
            "results": []
        }
    
    try:
        return tool.search_func(**kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


# =============================================================================
# TOOL SCHEMA HELPERS
# =============================================================================

def create_openai_schema(
    name: str,
    description: str,
    parameters: Dict
) -> Dict:
    """Erstellt ein OpenAI-kompatibles Tool-Schema."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    }


def create_anthropic_schema(
    name: str,
    description: str,
    parameters: Dict
) -> Dict:
    """Erstellt ein Anthropic-kompatibles Tool-Schema."""
    return {
        "name": name,
        "description": description,
        "input_schema": parameters
    }
