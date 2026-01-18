"""
HayMAS Writer Agent

Schreibt hochwertige Wissensartikel aus Recherche-Ergebnissen.
Nutzt GPT-5.2 für beste Textqualität.
"""

from typing import Dict, Any, List, Generator, Literal
import os

from .base_agent import BaseAgent, AgentEvent, EventType

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import ARTICLE_TARGET_SECTIONS, ARTICLE_MIN_WORDS


WRITER_SYSTEM_PROMPT = """Du bist ein Writer-Agent, der hochwertige Wissensartikel erstellt.

## DEINE AUFGABE
Erstelle einen umfassenden, gut strukturierten Wissensartikel aus den Recherche-Ergebnissen.

## ARTIKEL-STRUKTUR (MUSS so aufgebaut sein!)

```markdown
# [Thema der Kernfrage]

## Management Summary
3-5 Sätze, die die Kernerkenntnisse zusammenfassen.
Für Leser, die wenig Zeit haben.

## 1. Einführung & Kontext
- Warum ist dieses Thema relevant?
- Für wen ist dieser Artikel?
- Was wird behandelt?

## 2. Grundlagen & Konzepte
- Definitionen
- Grundlegende Funktionsweise
- Einordnung ins große Ganze

## 3. Aktuelle Entwicklungen
- Neueste Trends und News (mit Datum!)
- Aktuelle Releases und Features
- Marktentwicklung

## 4. [Themenspezifischer Deep-Dive]
- Technische Details
- Konkrete Funktionsweisen
- Vor- und Nachteile

## 5. Praxisbeispiele
- Reale Anwendungsfälle
- Case Studies
- Lessons Learned

## 6. Kritische Einordnung
- Limitationen und Herausforderungen
- Alternative Ansätze
- Offene Fragen

## 7. Fazit & Ausblick
- Zusammenfassung der Kernpunkte
- Empfehlungen
- Zukünftige Entwicklungen

## Quellen
- [1] Titel, URL
- [2] Titel, URL
...
```

## REGELN

1. **Relevanz**: Der Artikel MUSS die KERNFRAGE beantworten!
2. **Tiefe**: Mindestens 2000 Wörter, jeder Abschnitt substantiell
3. **Fakten**: Nutze die Recherche-Ergebnisse, erfinde nichts!
4. **Quellen**: Jede wichtige Aussage mit Quelle belegen
5. **Lesbarkeit**: Klare Struktur, verständliche Sprache
6. **Konkret**: Echte Zahlen, Beispiele, keine leeren Phrasen

## VERBOTEN
- Leere Abschnitte oder Platzhalter
- "Siehe Anhang" oder ähnliche Verweise
- Allgemeine Phrasen ohne Inhalt
- Abweichen vom Thema der Kernfrage

## SPRACHE
Deutsch, professionell aber verständlich.
"""


class WriterAgent(BaseAgent):
    """
    Writer Agent für hochwertige Wissensartikel.
    Nutzt GPT-5.2 oder GPT-5.1.
    """
    
    def __init__(self, tier: Literal["premium", "budget"] = "premium"):
        super().__init__(
            name="Writer",
            system_prompt=WRITER_SYSTEM_PROMPT,
            agent_type="writer",
            tier=tier,
            tools=["save_markdown"]
        )
    
    def write_article(
        self, 
        task: str,
        context: Dict[str, Any] = None
    ) -> Generator[AgentEvent, None, str]:
        """
        Schreibt einen Wissensartikel.
        
        Args:
            task: Schreibauftrag
            context: Enthält research_results und core_question
        
        Yields:
            AgentEvents
        
        Returns:
            Der geschriebene Artikel als Markdown
        """
        # Kontext aufbereiten
        core_question = context.get("core_question", "") if context else ""
        research = context.get("research_results", "") if context else ""
        editor_feedback = context.get("editor_feedback", "") if context else ""
        
        full_task = f"""## SCHREIB-AUFTRAG

### KERNFRAGE (Das Thema des Artikels!):
{core_question}

### Auftrag:
{task}

### Recherche-Ergebnisse (nutze diese als Basis!):
{research[:8000] if research else "Keine Recherche vorhanden."}

{"### Editor-Feedback (berücksichtige dies!):" + chr(10) + editor_feedback if editor_feedback else ""}

## ANWEISUNGEN:
1. Schreibe einen VOLLSTÄNDIGEN Artikel nach der vorgegebenen Struktur
2. Der Artikel MUSS die KERNFRAGE beantworten
3. Nutze die Recherche-Ergebnisse als Faktengrundlage
4. Mindestens 2000 Wörter, substantiell und tiefgehend
5. Gib den kompletten Artikel als Markdown aus

## JETZT: Schreibe den Artikel!"""

        result = ""
        for event in self.run(full_task, context):
            yield event
            if event.event_type == EventType.RESPONSE:
                result = event.content
        
        return result
