"""
HayMAS Tools - Verfügbare Tools für MCP Server

Die Tool-Registry wird automatisch befüllt, wenn die Tool-Module importiert werden.
"""

# Registry zuerst importieren
from .registry import (
    get_all_tools,
    get_tool,
    get_tools_for_topic,
    get_tools_for_api,
    get_tools_description_for_prompt,
    execute_tool,
    ResearchTool,
    ToolCategory
)

# Tools importieren (registrieren sich selbst in der Registry)
from .tavily_search import tavily_search
from .wikipedia_tool import wikipedia_search
from .gnews_tool import gnews_search
from .hackernews_tool import hackernews_search
from .semantic_scholar_tool import semantic_scholar_search
from .arxiv_tool import arxiv_search
from .ted_tool import ted_search

# Legacy Tools
from .ppt_generator import create_ppt
from .file_tools import save_markdown, read_markdown

__all__ = [
    # Registry
    "get_all_tools",
    "get_tool",
    "get_tools_for_topic",
    "get_tools_for_api",
    "get_tools_description_for_prompt",
    "execute_tool",
    "ResearchTool",
    "ToolCategory",
    
    # Research Tools (Funktionen)
    "tavily_search",
    "wikipedia_search",
    "gnews_search",
    "hackernews_search",
    "semantic_scholar_search",
    "arxiv_search",
    "ted_search",
    
    # Legacy Tools
    "create_ppt",
    "save_markdown", 
    "read_markdown"
]
