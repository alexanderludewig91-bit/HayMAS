"""
Datei-Tools für HayMAS

Ermöglicht Agenten, Markdown-Dateien zu speichern und zu lesen.
"""

import os
from datetime import datetime
from typing import Dict, Any

# Standard Output-Verzeichnis
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")


def ensure_output_dir():
    """Stellt sicher, dass das Output-Verzeichnis existiert"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_markdown(content: str, filename: str = None) -> Dict[str, Any]:
    """
    Speichert Markdown-Inhalt in eine Datei.
    
    Args:
        content: Der Markdown-Inhalt
        filename: Optional - Dateiname (ohne .md). 
                  Falls nicht angegeben, wird ein Timestamp verwendet.
    
    Returns:
        Dict mit:
        - success: bool
        - filepath: Pfad zur gespeicherten Datei
        - filename: Name der Datei
        - error: Optional - Fehlermeldung
    """
    try:
        ensure_output_dir()
        
        # Dateiname generieren falls nicht angegeben
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"praesentation_{timestamp}"
        
        # .md Endung hinzufügen falls nicht vorhanden
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Datei schreiben
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "filepath": filepath,
            "filename": filename,
            "content_length": len(content)
        }
        
    except Exception as e:
        return {
            "success": False,
            "filepath": None,
            "filename": filename,
            "error": str(e)
        }


def read_markdown(filename: str) -> Dict[str, Any]:
    """
    Liest eine Markdown-Datei aus dem Output-Verzeichnis.
    
    Args:
        filename: Name der Datei (mit oder ohne .md)
    
    Returns:
        Dict mit:
        - success: bool
        - content: Inhalt der Datei
        - filepath: Pfad zur Datei
        - error: Optional - Fehlermeldung
    """
    try:
        # .md Endung hinzufügen falls nicht vorhanden
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if not os.path.exists(filepath):
            return {
                "success": False,
                "content": None,
                "filepath": filepath,
                "error": f"Datei nicht gefunden: {filename}"
            }
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "filepath": filepath,
            "content_length": len(content)
        }
        
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "filepath": None,
            "error": str(e)
        }


# Tool-Definitionen für LLM Function Calling (OpenAI Format)
SAVE_MARKDOWN_TOOL = {
    "type": "function",
    "function": {
        "name": "save_markdown",
        "description": "Speichert Markdown-Inhalt (z.B. die Folien-Struktur) in eine Datei für spätere Verwendung.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Der Markdown-Inhalt der gespeichert werden soll"
                },
                "filename": {
                    "type": "string",
                    "description": "Dateiname ohne .md Endung. Falls nicht angegeben wird ein Timestamp verwendet."
                }
            },
            "required": ["content"]
        }
    }
}

READ_MARKDOWN_TOOL = {
    "type": "function",
    "function": {
        "name": "read_markdown",
        "description": "Liest eine zuvor gespeicherte Markdown-Datei.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name der zu lesenden Datei"
                }
            },
            "required": ["filename"]
        }
    }
}

# Anthropic Tool-Format
SAVE_MARKDOWN_TOOL_ANTHROPIC = {
    "name": "save_markdown",
    "description": "Speichert Markdown-Inhalt (z.B. die Folien-Struktur) in eine Datei für spätere Verwendung.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Der Markdown-Inhalt der gespeichert werden soll"
            },
            "filename": {
                "type": "string",
                "description": "Dateiname ohne .md Endung. Falls nicht angegeben wird ein Timestamp verwendet."
            }
        },
        "required": ["content"]
    }
}

READ_MARKDOWN_TOOL_ANTHROPIC = {
    "name": "read_markdown",
    "description": "Liest eine zuvor gespeicherte Markdown-Datei.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Name der zu lesenden Datei"
            }
        },
        "required": ["filename"]
    }
}
