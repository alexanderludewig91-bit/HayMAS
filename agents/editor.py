"""
HayMAS Editor Agent

Prueft Wissensartikel auf Qualitaet und gibt konstruktives Feedback.
Nutzt Claude Sonnet 4.5 fuer kritische Analyse.

NEU: Strukturiertes Feedback mit EditorVerdict fuer Smart Editor-Routing.
"""

from typing import Dict, Any, List, Generator, Literal, Optional
from dataclasses import dataclass, field
import os
import json
import re

from .base_agent import BaseAgent, AgentEvent, EventType

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


@dataclass
class EditorIssue:
    """Ein einzelnes vom Editor identifiziertes Problem"""
    type: str
    description: str
    severity: str
    suggested_action: str
    research_query: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "severity": self.severity,
            "suggested_action": self.suggested_action,
            "research_query": self.research_query
        }


@dataclass
class EditorVerdict:
    """Strukturiertes Editor-Urteil fuer Smart Routing."""
    verdict: str
    confidence: float
    issues: List[EditorIssue] = field(default_factory=list)
    summary: str = ""
    raw_feedback: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "issues": [issue.to_dict() for issue in self.issues],
            "summary": self.summary,
            "raw_feedback": self.raw_feedback
        }
    
    @classmethod
    def from_response(cls, response_text: str) -> "EditorVerdict":
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                issues = []
                for issue_data in data.get("issues", []):
                    issues.append(EditorIssue(
                        type=issue_data.get("type", "style"),
                        description=issue_data.get("description", ""),
                        severity=issue_data.get("severity", "minor"),
                        suggested_action=issue_data.get("suggested_action", "revise"),
                        research_query=issue_data.get("research_query")
                    ))
                return cls(
                    verdict=data.get("verdict", "revise"),
                    confidence=float(data.get("confidence", 0.5)),
                    issues=issues,
                    summary=data.get("summary", ""),
                    raw_feedback=response_text
                )
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        verdict = "revise"
        response_lower = response_text.lower()
        if "gesamtbewertung: gut" in response_lower:
            verdict = "approved"
        elif "mangelhaft" in response_lower:
            verdict = "research"
        elif any(kw in response_lower for kw in ["quelle fehlt", "beleg fehlt"]):
            verdict = "research"
        
        return cls(verdict=verdict, confidence=0.4, issues=[], 
                   summary="Fallback", raw_feedback=response_text)
    
    def has_content_gaps(self) -> bool:
        return any(i.type == "content_gap" and i.suggested_action == "research" for i in self.issues)
    
    def get_research_queries(self) -> List[str]:
        return [i.research_query for i in self.issues if i.research_query and i.suggested_action == "research"]


EDITOR_SYSTEM_PROMPT = """Du bist ein Editor-Agent, der Wissensartikel kritisch prueft.

## PRUEFKRITERIEN
1. Relevanz - Beantwortet der Artikel die KERNFRAGE?
2. Vollstaendigkeit - Alle erforderlichen Abschnitte?
3. Tiefe - Echte Fakten und Zahlen?
4. Quellen - Sind Quellen angegeben?
5. Lesbarkeit - Logische Struktur?

## OUTPUT-FORMAT (ZWEI TEILE!)

### Teil 1: Markdown-Feedback
## Editor-Bewertung
### Gesamtbewertung: [GUT/VERBESSERUNGSWUERDIG/MANGELHAFT]
### Staerken
- [Was gut ist]
### Verbesserungsbedarf
1. **[Problem 1]**: [Beschreibung]
### Empfehlung
[Konkrete Handlungsempfehlung]

### Teil 2: PFLICHT - JSON am Ende!
```json
{
  "verdict": "approved|revise|research",
  "confidence": 0.0-1.0,
  "issues": [{"type": "style|structure|content_gap|factual_error", "description": "...", "severity": "minor|major|critical", "suggested_action": "revise|research", "research_query": "..."}],
  "summary": "..."
}
```

## ENTSCHEIDUNGSLOGIK:
- "approved": Artikel ist GUT
- "revise": Stilistisch/strukturell -> Writer kann beheben
- "research": Inhaltliche Luecken -> Nachrecherche noetig
"""


class EditorAgent(BaseAgent):
    """Editor Agent fuer Qualitaetspruefung."""
    
    def __init__(self, tier: Literal["premium", "budget"] = "premium"):
        super().__init__(
            name="Editor",
            system_prompt=EDITOR_SYSTEM_PROMPT,
            agent_type="editor",
            tier=tier,
            tools=["read_markdown"]
        )
    
    def review_article(self, task: str, context: Dict[str, Any] = None) -> Generator[AgentEvent, None, str]:
        core_question = context.get("core_question", "") if context else ""
        article = context.get("article", "") if context else ""
        
        full_task = f"""## PRUEF-AUFTRAG
### KERNFRAGE: {core_question}
### Auftrag: {task}
### ZU PRUEFENDER ARTIKEL:
{article[:12000] if article else "Kein Artikel."}

WICHTIG: Haenge am Ende das strukturierte JSON-Objekt an!"""

        result = ""
        for event in self.run(full_task, context):
            yield event
            if event.event_type == EventType.RESPONSE:
                result = event.content
        return result
    
    def review_article_structured(self, task: str, context: Dict[str, Any] = None) -> Generator[AgentEvent, None, "EditorVerdict"]:
        raw_feedback = ""
        for event in self.review_article(task, context):
            yield event
            if event.event_type == EventType.RESPONSE:
                raw_feedback = event.content
        
        verdict = EditorVerdict.from_response(raw_feedback)
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"Editor-Verdict: {verdict.verdict.upper()}",
            data=verdict.to_dict()
        )
        return verdict
