"""
Prompt Optimizer Agent

Analysiert User-Anfragen und generiert optimierte Prompts
mit expliziten Parametern für das Evidence-Gated System.
"""

import json
import re
from typing import Dict, Any, Generator, Optional
from dataclasses import dataclass, asdict

from agents.base_agent import BaseAgent, AgentEvent, EventType


@dataclass
class PromptAnalysis:
    """Analyse der User-Anfrage"""
    detected_topic: str
    detected_format: str  # "overview" | "article" | "report" | "deep_dive"
    detected_audience: str  # "experts" | "management" | "general"
    suggested_questions: list  # Rückfragen falls unklar
    confidence: float


@dataclass 
class OptimizedPrompt:
    """Optimierter Prompt mit expliziten Parametern"""
    prompt_text: str
    parameters: Dict[str, Any]
    explanation: str


PROMPT_OPTIMIZER_SYSTEM = """Du bist ein Prompt-Optimierer für ein wissenschaftliches Artikel-System.

## DEINE AUFGABE
Analysiere die User-Anfrage und erstelle einen optimierten Prompt, der zu hochwertigen Ergebnissen führt.

## WAS DU WEISST ÜBER DAS SYSTEM
- Das System erstellt Expertenberichte mit 10-15+ Seiten
- Es nutzt Claims (prüfbare Aussagen) und recherchiert gezielt Quellen
- Gute Ergebnisse entstehen bei:
  - Klarer Zielgruppe (Fachexperten vs. Management vs. Allgemein)
  - Definiertem Format (Expertenbericht > Artikel > Übersicht)
  - Konkretem Fokus (was soll behandelt werden, was nicht)

## OUTPUT FORMAT (NUR JSON!)

```json
{
  "analysis": {
    "detected_topic": "Das erkannte Hauptthema",
    "detected_format": "overview|article|report|deep_dive",
    "detected_audience": "experts|management|general",
    "suggested_questions": ["Rückfrage 1 falls nötig", "Rückfrage 2"],
    "confidence": 0.8
  },
  "optimized_prompt": {
    "prompt_text": "Der optimierte Prompt-Text",
    "parameters": {
      "target_pages": 12,
      "audience": "Fachexperten",
      "tone": "wissenschaftlich",
      "format": "Expertenbericht"
    },
    "explanation": "Warum dieser Prompt besser ist"
  }
}
```

## REGELN FÜR DEN OPTIMIERTEN PROMPT

1. **Format-Keyword setzen**:
   - "Übersicht" → "Erstelle eine kompakte Übersicht (3-5 Seiten)..."
   - "Artikel" → "Erstelle einen Fachartikel (8-10 Seiten)..."
   - "Expertenbericht" → "Erstelle einen Expertenbericht (10-15 Seiten)..."
   - "Deep-Dive" → "Erstelle eine umfassende Deep-Dive Analyse (15-20 Seiten)..."

2. **Zielgruppe explizit nennen**:
   - "...für Fachexperten im Bereich..."
   - "...für IT-Entscheider und Management..."
   - "...für Einsteiger in das Thema..."

3. **Fokus präzisieren**:
   - Was soll behandelt werden
   - Was soll NICHT behandelt werden (Scope out)
   - Welche Aspekte sind besonders wichtig

4. **Konkrete Beispiele/Systeme nennen** wenn im Original erwähnt

## BEISPIEL

User: "Übersicht e-Akten Deutschland"

Analyse:
- detected_topic: "E-Aktensysteme in Deutschland"
- detected_format: "overview"
- detected_audience: "experts" (nicht spezifiziert, Default)
- confidence: 0.6 (Zielgruppe unklar)

Optimierter Prompt:
"Erstelle einen Expertenbericht (10-15 Seiten) über elektronische Aktensysteme (e-Akte) in Deutschland für Fachexperten im Bereich öffentliche Verwaltung und IT.

Der Bericht soll folgende Aspekte behandeln:
- Marktübersicht der führenden Anbieter und Systeme
- Unterscheidung dokumenten- vs. datenzentrierte Ansätze
- Rechtliche Rahmenbedingungen (E-Government-Gesetz, OZG)
- Aktueller Implementierungsstand in Bund, Ländern und Kommunen

Nicht im Fokus: Elektronische Patientenakte (ePA), Systeme außerhalb Deutschlands."
"""


class PromptOptimizerAgent(BaseAgent):
    """
    Leichtgewichtiger Agent zur Prompt-Optimierung.
    Nutzt ein schnelles/günstiges Modell.
    """
    
    def __init__(self):
        super().__init__(
            name="PromptOptimizer",
            system_prompt=PROMPT_OPTIMIZER_SYSTEM,
            agent_type="orchestrator",  # Nutzt Orchestrator-Tier
            tier="budget",  # Günstigeres Modell reicht
            tools=[]
        )
    
    def analyze_and_optimize(
        self,
        user_input: str,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Generator[AgentEvent, None, Dict[str, Any]]:
        """
        Analysiert die User-Anfrage und generiert einen optimierten Prompt.
        
        Args:
            user_input: Die ursprüngliche User-Anfrage
            user_preferences: Optional - bereits vom User gewählte Optionen
            
        Yields:
            AgentEvents
            
        Returns:
            Dict mit "analysis" und "optimized_prompt"
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="🔧 Analysiere Anfrage und optimiere Prompt..."
        )
        
        # Preferences einbauen falls vorhanden
        preferences_str = ""
        if user_preferences:
            preferences_str = f"""
## USER-PRÄFERENZEN (bereits gewählt)
- Format: {user_preferences.get('format', 'nicht gewählt')}
- Zielgruppe: {user_preferences.get('audience', 'nicht gewählt')}
- Seitenzahl: {user_preferences.get('pages', 'nicht gewählt')}

Berücksichtige diese Präferenzen im optimierten Prompt!
"""
        
        task = f"""Analysiere folgende User-Anfrage und erstelle einen optimierten Prompt:

USER-ANFRAGE: {user_input}
{preferences_str}
Antworte NUR mit dem JSON-Objekt!"""

        result_text = ""
        for event in self.run(task):
            yield event
            if event.event_type == EventType.RESPONSE:
                result_text = event.content
        
        # JSON parsen
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Versuche direktes JSON zu finden
                json_str = result_text.strip()
                if not json_str.startswith('{'):
                    # Suche nach { ... }
                    brace_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if brace_match:
                        json_str = brace_match.group(0)
            
            data = json.loads(json_str)
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"✅ Prompt optimiert (Konfidenz: {data.get('analysis', {}).get('confidence', 0):.0%})"
            )
            
            return data
            
        except (json.JSONDecodeError, KeyError) as e:
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name=self.name,
                content=f"❌ JSON-Parsing fehlgeschlagen: {e}"
            )
            
            # Fallback
            return {
                "analysis": {
                    "detected_topic": user_input,
                    "detected_format": "report",
                    "detected_audience": "experts",
                    "suggested_questions": [],
                    "confidence": 0.5
                },
                "optimized_prompt": {
                    "prompt_text": f"Erstelle einen Expertenbericht (10-15 Seiten) über: {user_input}",
                    "parameters": {
                        "target_pages": 12,
                        "audience": "Fachexperten",
                        "tone": "wissenschaftlich",
                        "format": "Expertenbericht"
                    },
                    "explanation": "Fallback-Optimierung wegen Parsing-Fehler"
                }
            }
    
    def quick_optimize(
        self,
        user_input: str,
        format_choice: str,
        audience_choice: str
    ) -> Dict[str, Any]:
        """
        Schnelle Optimierung ohne LLM-Call basierend auf User-Auswahl.
        
        Args:
            user_input: Original-Anfrage
            format_choice: "overview" | "article" | "report" | "deep_dive"
            audience_choice: "experts" | "management" | "general"
            
        Returns:
            Optimierter Prompt als Dict
        """
        # Format-Mapping
        format_config = {
            "overview": {
                "prefix": "Erstelle eine kompakte Übersicht",
                "pages": "3-5",
                "target_pages": 4,
                "label": "Kompakte Übersicht"
            },
            "article": {
                "prefix": "Erstelle einen Fachartikel",
                "pages": "8-10",
                "target_pages": 9,
                "label": "Fachartikel"
            },
            "report": {
                "prefix": "Erstelle einen Expertenbericht",
                "pages": "10-15",
                "target_pages": 12,
                "label": "Expertenbericht"
            },
            "deep_dive": {
                "prefix": "Erstelle eine umfassende Deep-Dive Analyse",
                "pages": "15-20",
                "target_pages": 17,
                "label": "Deep-Dive Analyse"
            }
        }
        
        # Audience-Mapping
        audience_config = {
            "experts": {
                "suffix": "für Fachexperten",
                "tone": "wissenschaftlich",
                "label": "Fachexperten"
            },
            "management": {
                "suffix": "für IT-Entscheider und Management",
                "tone": "praxisorientiert",
                "label": "Management"
            },
            "general": {
                "suffix": "für Einsteiger in das Thema",
                "tone": "erklaerend",
                "label": "Allgemein"
            }
        }
        
        fmt = format_config.get(format_choice, format_config["report"])
        aud = audience_config.get(audience_choice, audience_config["experts"])
        
        prompt_text = f"{fmt['prefix']} ({fmt['pages']} Seiten) {aud['suffix']} über: {user_input}"
        
        return {
            "analysis": {
                "detected_topic": user_input,
                "detected_format": format_choice,
                "detected_audience": audience_choice,
                "suggested_questions": [],
                "confidence": 1.0  # User hat explizit gewählt
            },
            "optimized_prompt": {
                "prompt_text": prompt_text,
                "parameters": {
                    "target_pages": fmt["target_pages"],
                    "audience": aud["label"],
                    "tone": aud["tone"],
                    "format": format_choice  # Value ("report") statt Label ("Expertenbericht")
                },
                "explanation": f"Optimiert für {fmt['label']} ({fmt['pages']} Seiten) für {aud['label']}"
            }
        }
