"""
HayMAS MCP Server

Stellt Tools für die Agenten bereit und verwaltet Tool-Aufrufe.
Dies ist eine vereinfachte MCP-Implementation für den Prototypen.

Die Research-Tools werden automatisch aus der Tool-Registry geladen.
"""

from typing import Dict, Any, Callable, List
from dataclasses import dataclass, field

# Research Tools aus der Registry
from .tools.registry import get_all_tools as get_all_research_tools, get_tool as get_research_tool

# Legacy Tools (Datei-Operationen, PPT)
from .tools.file_tools import (
    save_markdown, 
    read_markdown,
    SAVE_MARKDOWN_TOOL,
    READ_MARKDOWN_TOOL,
    SAVE_MARKDOWN_TOOL_ANTHROPIC,
    READ_MARKDOWN_TOOL_ANTHROPIC
)
from .tools.ppt_generator import (
    create_ppt,
    CREATE_PPT_TOOL,
    CREATE_PPT_TOOL_ANTHROPIC
)


@dataclass
class ToolRegistry:
    """Registry für verfügbare Tools"""
    
    # Mapping von Tool-Namen zu Funktionen
    _tools: Dict[str, Callable] = field(default_factory=dict)
    
    # Tool-Definitionen für OpenAI Format
    _openai_tools: Dict[str, Dict] = field(default_factory=dict)
    
    # Tool-Definitionen für Anthropic Format
    _anthropic_tools: Dict[str, Dict] = field(default_factory=dict)
    
    def register(
        self, 
        name: str, 
        func: Callable, 
        openai_def: Dict, 
        anthropic_def: Dict
    ):
        """Registriert ein Tool"""
        self._tools[name] = func
        self._openai_tools[name] = openai_def
        self._anthropic_tools[name] = anthropic_def
    
    def get_tool(self, name: str) -> Callable:
        """Gibt die Funktion für ein Tool zurück"""
        return self._tools.get(name)
    
    def get_openai_tools(self, names: List[str] = None) -> List[Dict]:
        """Gibt Tool-Definitionen im OpenAI Format zurück"""
        if names:
            return [self._openai_tools[n] for n in names if n in self._openai_tools]
        return list(self._openai_tools.values())
    
    def get_anthropic_tools(self, names: List[str] = None) -> List[Dict]:
        """Gibt Tool-Definitionen im Anthropic Format zurück"""
        if names:
            return [self._anthropic_tools[n] for n in names if n in self._anthropic_tools]
        return list(self._anthropic_tools.values())
    
    def call_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Ruft ein Tool mit den gegebenen Argumenten auf"""
        tool = self.get_tool(name)
        if tool is None:
            return {
                "success": False,
                "error": f"Tool '{name}' nicht gefunden"
            }
        try:
            return tool(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Fehler bei Tool-Aufruf: {str(e)}"
            }


class MCPServer:
    """
    MCP Server für HayMAS
    
    Verwaltet die verfügbaren Tools und deren Aufrufe.
    Research-Tools werden automatisch aus der Tool-Registry geladen.
    """
    
    def __init__(self):
        self.registry = ToolRegistry()
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Registriert alle verfügbaren Tools"""
        
        # =================================================================
        # RESEARCH TOOLS (aus der neuen Tool-Registry)
        # =================================================================
        # Import der Tools triggert deren Registrierung in der Research-Registry
        from .tools import tavily_search, wikipedia_search, gnews_search, hackernews_search
        
        # Research-Tools aus der Registry laden und hier registrieren
        for research_tool in get_all_research_tools():
            if research_tool.search_func and research_tool.tool_schema_openai:
                self.registry.register(
                    name=f"{research_tool.id}_search",
                    func=research_tool.search_func,
                    openai_def=research_tool.tool_schema_openai,
                    anthropic_def=research_tool.tool_schema_anthropic
                )
        
        # =================================================================
        # LEGACY TOOLS (Datei-Operationen, PPT)
        # =================================================================
        
        # Datei-Operationen
        self.registry.register(
            name="save_markdown",
            func=save_markdown,
            openai_def=SAVE_MARKDOWN_TOOL,
            anthropic_def=SAVE_MARKDOWN_TOOL_ANTHROPIC
        )
        
        self.registry.register(
            name="read_markdown",
            func=read_markdown,
            openai_def=READ_MARKDOWN_TOOL,
            anthropic_def=READ_MARKDOWN_TOOL_ANTHROPIC
        )
        
        # PPT-Generierung
        self.registry.register(
            name="create_ppt",
            func=create_ppt,
            openai_def=CREATE_PPT_TOOL,
            anthropic_def=CREATE_PPT_TOOL_ANTHROPIC
        )
    
    def get_tools_for_agent(
        self, 
        agent_type: str, 
        provider: str = "anthropic",
        specific_tools: List[str] = None
    ) -> List[Dict]:
        """
        Gibt die Tools zurück, die ein bestimmter Agent nutzen darf.
        
        Args:
            agent_type: "orchestrator", "researcher", "structurer"
            provider: "anthropic" oder "openai"
            specific_tools: Optional - Liste spezifischer Tools (überschreibt defaults)
        
        Returns:
            Liste von Tool-Definitionen
        """
        # Tool-Zuordnung pro Agent (Defaults)
        agent_tools = {
            "orchestrator": [],  # Orchestrator ruft andere Agenten auf, keine direkten Tools
            "researcher": ["tavily_search"],  # Default, kann überschrieben werden
            "writer": ["save_markdown"],  # Writer speichert Artikel
            "editor": ["read_markdown"],   # Editor liest Artikel
            "structurer": ["save_markdown", "read_markdown"],  # Legacy
            "ppt_generator": ["create_ppt"]  # Optional für PPT
        }
        
        # Spezifische Tools überschreiben die Defaults
        if specific_tools:
            allowed_tools = specific_tools
        else:
            allowed_tools = agent_tools.get(agent_type, [])
        
        # Filtern auf erlaubte Tools
        if not allowed_tools:
            return []
        
        if provider == "anthropic":
            return self.registry.get_anthropic_tools(allowed_tools)
        else:
            return self.registry.get_openai_tools(allowed_tools)
    
    def get_research_tools_info(self) -> List[Dict]:
        """
        Gibt Informationen über alle verfügbaren Research-Tools zurück.
        Für API und Frontend.
        """
        from .tools import get_tools_for_api
        return get_tools_for_api()
    
    def get_research_tools_for_topic(self, topic_type: str) -> List[str]:
        """
        Gibt empfohlene Research-Tools für einen Thementyp zurück.
        
        Args:
            topic_type: z.B. "tech", "science", "business"
        
        Returns:
            Liste von Tool-IDs
        """
        from .tools import get_tools_for_topic
        tools = get_tools_for_topic(topic_type)
        return [f"{t.id}_search" for t in tools]
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ruft ein Tool auf.
        
        Args:
            name: Name des Tools
            arguments: Argumente für das Tool
        
        Returns:
            Ergebnis des Tool-Aufrufs
        """
        return self.registry.call_tool(name, **arguments)
    
    def list_tools(self) -> List[str]:
        """Gibt eine Liste aller verfügbaren Tool-Namen zurück"""
        return list(self.registry._tools.keys())


# Globale Server-Instanz
_server_instance = None


def get_mcp_server() -> MCPServer:
    """Gibt die globale MCP Server Instanz zurück (Singleton)"""
    global _server_instance
    if _server_instance is None:
        _server_instance = MCPServer()
    return _server_instance
