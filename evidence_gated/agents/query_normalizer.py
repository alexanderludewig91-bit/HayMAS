"""
Query Normalizer Agent - Phase 1

Präzisiert die Fragestellung und erstellt TermMap.
Löst Ambiguitäten und definiert Scope.
"""

import json
import re
from typing import Dict, Any, Generator
from datetime import date

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import QuestionBrief, TermMap


QUERY_NORMALIZER_PROMPT = """Du bist ein Query Normalizer Agent für wissenschaftliche Recherche.

## DEINE AUFGABE
Analysiere die User-Frage und erstelle:
1. **QuestionBrief**: Präzisierte Fragestellung mit Scope
2. **TermMap**: Terminologie-Mapping für präzise Suchen

## WARUM DAS WICHTIG IST
- Ambiguität führt zu falschen Suchergebnissen
- "Agent Builder" ≠ "Build Agent" - solche Unterschiede müssen erfasst werden!
- Ohne klaren Scope wird die Recherche zu breit

## OUTPUT FORMAT (NUR JSON!)

```json
{
  "question_brief": {
    "core_question": "Präzisierte Version der Frage",
    "original_question": "Ursprüngliche Frage",
    "audience": "Fachexperten|Management|Allgemein",
    "tone": "wissenschaftlich|praxisorientiert|erklaerend",
    "target_pages": 12,
    "as_of_date": "YYYY-MM-DD",
    "freshness_priority": "high|medium|low",
    "scope_in": ["Was behandelt werden soll"],
    "scope_out": ["Was explizit ausgeschlossen ist"]
  },
  "term_map": {
    "canonical_terms": ["Hauptbegriff1", "Hauptbegriff2"],
    "synonyms": {
      "Hauptbegriff1": ["Synonym1", "Synonym2"]
    },
    "negative_keywords": ["Begriffe die zu falschen Treffern fuehren"],
    "disambiguation_notes": ["Begriff X meint hier Y, nicht Z"],
    "search_variants": {
      "Hauptbegriff1": ["Suchvariante1", "Suchvariante2", "englische Variante"]
    }
  }
}
```

## REGELN
1. IMMER 3-5 Suchvarianten pro kanonischem Term (inkl. Englisch!)
2. IMMER Negative Keywords setzen wenn es bekannte Verwechslungen gibt
3. IMMER Disambiguation Notes wenn ein Begriff mehrdeutig ist
4. Scope klar definieren - was ist IN, was ist OUT?
5. Freshness-Priority basierend auf Themenaktualität setzen

## BEISPIEL
User fragt: "Was ist ServiceNow Agent Builder?"

Gute TermMap:
- canonical_terms: ["ServiceNow Build Agent", "AI Agent Studio"]
- synonyms: {"ServiceNow Build Agent": ["Build Agent", "Agent Builder", "Agentic AI Builder"]}
- negative_keywords: ["Jenkins Agent", "Azure DevOps Agent", "Build-Agent (CI/CD)"]
- disambiguation_notes: ["'Agent Builder' ist KEIN offizielles Produkt - ServiceNow nennt es 'Build Agent' oder 'AI Agent Studio'"]
- search_variants: {"ServiceNow Build Agent": ["ServiceNow Build Agent", "ServiceNow AI Agent Studio", "Now Platform Agentic AI", "ServiceNow agent development"]}
"""


class QueryNormalizerAgent(BaseAgent):
    """
    Phase 1: Query Normalization
    
    Präzisiert die Fragestellung und erstellt TermMap.
    """
    
    def __init__(self, tier: str = "premium"):
        super().__init__(
            name="QueryNormalizer",
            system_prompt=QUERY_NORMALIZER_PROMPT,
            agent_type="orchestrator",  # Nutzt Orchestrator-Modell für gute Analyse
            tier=tier,
            tools=[]  # Keine Tools - reine Analyse
        )
    
    def normalize(
        self, 
        question: str
    ) -> Generator[AgentEvent, None, Dict[str, Any]]:
        """
        Normalisiert eine User-Frage.
        
        Args:
            question: Die ursprüngliche User-Frage
        
        Yields:
            AgentEvents
        
        Returns:
            Dict mit "question_brief" und "term_map"
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="🔍 Analysiere Fragestellung und erstelle TermMap..."
        )
        
        task = f"""Analysiere folgende Frage und erstelle QuestionBrief + TermMap:

FRAGE: {question}

HEUTIGES DATUM: {date.today().isoformat()}

Antworte NUR mit dem JSON-Objekt, kein anderer Text!"""

        result_text = ""
        for event in self.run(task):
            yield event
            if event.event_type == EventType.RESPONSE:
                result_text = event.content
        
        # JSON parsen
        try:
            # JSON aus Markdown-Block extrahieren falls vorhanden
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text.strip()
            
            data = json.loads(json_str)
            
            question_brief = QuestionBrief.from_dict(data["question_brief"])
            term_map = TermMap.from_dict(data["term_map"])
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"✅ TermMap erstellt: {len(term_map.canonical_terms)} Begriffe, {len(term_map.negative_keywords)} Negative Keywords",
                data={
                    "canonical_terms": term_map.canonical_terms,
                    "search_variants_count": sum(len(v) for v in term_map.search_variants.values())
                }
            )
            
            return {
                "question_brief": question_brief,
                "term_map": term_map
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name=self.name,
                content=f"❌ JSON-Parsing fehlgeschlagen: {e}"
            )
            
            # Fallback
            return {
                "question_brief": QuestionBrief(
                    core_question=question,
                    original_question=question,
                    audience="Fachexperten",
                    tone="wissenschaftlich",
                    as_of_date=date.today().isoformat(),
                    freshness_priority="medium"
                ),
                "term_map": TermMap(
                    canonical_terms=[question.split()[0]],
                    synonyms={},
                    negative_keywords=[],
                    disambiguation_notes=[],
                    search_variants={}
                )
            }
