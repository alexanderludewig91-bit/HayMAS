"""
HayMAS Agent Logging

Schreibt detaillierte Logs für jeden Durchlauf in eine MD-Datei.
"""

import os
from datetime import datetime
from typing import List, Dict, Any
import json


class AgentLogger:
    """Logger für Agent-Durchläufe"""
    
    def __init__(self, core_question: str, log_dir: str = None):
        self.core_question = core_question
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        self.events: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Generate filename
        safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in core_question[:30])
        safe_name = safe_name.strip().replace(" ", "_").lower()
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"log_{safe_name}_{timestamp}.md")
    
    def log_event(self, agent: str, event_type: str, content: str, data: Dict = None):
        """Loggt ein Event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "type": event_type,
            "content": content,
            "data": data or {}
        }
        self.events.append(event)
        
        # Bei Fehlern separat speichern
        if event_type == "error":
            self.errors.append(event)
    
    def log_error(self, agent: str, error: str, details: Dict = None):
        """Loggt einen Fehler explizit"""
        self.log_event(agent, "error", error, details)
    
    def log_api_call(self, agent: str, model: str, provider: str, success: bool, response_preview: str = ""):
        """Loggt einen API-Aufruf"""
        self.log_event(agent, "api_call", f"{provider}/{model} - {'OK' if success else 'FAIL'}", {
            "model": model,
            "provider": provider,
            "success": success,
            "response_preview": response_preview[:500] if response_preview else ""
        })
    
    def log_tool_call(self, agent: str, tool: str, args: Dict, result: Dict):
        """Loggt einen Tool-Aufruf"""
        self.log_event(agent, "tool_call", f"Tool: {tool}", {
            "tool": tool,
            "args": args,
            "result_success": result.get("success", False),
            "result_preview": str(result)[:500]
        })
    
    def save(self):
        """Speichert den Log als MD-Datei"""
        duration = datetime.now() - self.start_time
        
        content = f"""# HayMAS Durchlauf-Log

## Übersicht
- **Kernfrage:** {self.core_question}
- **Start:** {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}
- **Dauer:** {duration.total_seconds():.1f} Sekunden
- **Events:** {len(self.events)}
- **Fehler:** {len(self.errors)}

---

## Fehler-Zusammenfassung

"""
        if self.errors:
            for i, err in enumerate(self.errors, 1):
                content += f"""### Fehler {i}
- **Agent:** {err['agent']}
- **Zeit:** {err['timestamp']}
- **Meldung:** {err['content']}
- **Details:** 
```json
{json.dumps(err.get('data', {}), indent=2, ensure_ascii=False)[:1000]}
```

"""
        else:
            content += "*Keine Fehler aufgetreten.*\n\n"
        
        content += """---

## Event-Historie

| # | Zeit | Agent | Typ | Inhalt |
|---|------|-------|-----|--------|
"""
        for i, evt in enumerate(self.events, 1):
            time_str = evt['timestamp'].split('T')[1][:8] if 'T' in evt['timestamp'] else evt['timestamp']
            content_short = evt['content'][:60].replace('\n', ' ').replace('|', '/') + "..." if len(evt['content']) > 60 else evt['content'].replace('\n', ' ').replace('|', '/')
            content += f"| {i} | {time_str} | {evt['agent']} | {evt['type']} | {content_short} |\n"
        
        content += """
---

## Detaillierte Events

"""
        for i, evt in enumerate(self.events, 1):
            content += f"""### Event {i}: {evt['type']} ({evt['agent']})
**Zeit:** {evt['timestamp']}

**Inhalt:**
```
{evt['content'][:2000]}{"..." if len(evt['content']) > 2000 else ""}
```

"""
            if evt.get('data'):
                content += f"""**Daten:**
```json
{json.dumps(evt['data'], indent=2, ensure_ascii=False)[:1000]}
```

"""
        
        # Write to file
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return self.log_file


# Global logger instance
_current_logger = None


def get_logger() -> AgentLogger:
    """Gibt den aktuellen Logger zurück"""
    global _current_logger
    return _current_logger


def create_logger(core_question: str) -> AgentLogger:
    """Erstellt einen neuen Logger"""
    global _current_logger
    _current_logger = AgentLogger(core_question)
    return _current_logger
