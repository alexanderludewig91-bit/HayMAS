"""
HayMAS Editor Agent

Prüft Wissensartikel auf Qualität und gibt konstruktives Feedback.
Nutzt Claude Sonnet 4.5 für kritische Analyse.
"""

from typing import Dict, Any, List, Generator, Literal
import os

from .base_agent import BaseAgent, AgentEvent, EventType

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


EDITOR_SYSTEM_PROMPT = """Du bist ein Editor-Agent, der Wissensartikel kritisch prüft.

## DEINE AUFGABE
Analysiere den Artikel und prüfe folgende Qualitätskriterien:

## PRÜFKRITERIEN

### 1. Relevanz (Kritisch!)
- Beantwortet der Artikel die KERNFRAGE?
- Kommen alle wichtigen Aspekte vor?
- Gibt es Abweichungen vom Thema?

### 2. Vollständigkeit
- Hat der Artikel alle erforderlichen Abschnitte?
- Sind alle Abschnitte substantiell (nicht nur 1-2 Sätze)?
- Fehlen wichtige Informationen?

### 3. Tiefe
- Gibt es echte Fakten und Zahlen?
- Werden Konzepte erklärt oder nur erwähnt?
- Sind Beispiele konkret oder abstrakt?

### 4. Quellen
- Sind Quellen angegeben?
- Sind die Quellen glaubwürdig?
- Fehlen Quellenangaben bei wichtigen Aussagen?

### 5. Lesbarkeit
- Ist die Struktur logisch?
- Ist die Sprache verständlich?
- Gibt es Wiederholungen oder Inkonsistenzen?

## OUTPUT-FORMAT

```markdown
## Editor-Bewertung

### Gesamtbewertung: [GUT/VERBESSERUNGSWÜRDIG/MANGELHAFT]

### Stärken
- [Was gut ist]

### Verbesserungsbedarf
1. **[Problem 1]**: [Beschreibung und wie es verbessert werden sollte]
2. **[Problem 2]**: [Beschreibung und wie es verbessert werden sollte]

### Empfehlung
[Konkrete Handlungsempfehlung für den Writer]
```

## WICHTIG
- Sei konstruktiv aber ehrlich
- Konkrete Verbesserungsvorschläge statt allgemeiner Kritik
- Bei "GUT" sind nur kleine Verbesserungen nötig
- Bei "MANGELHAFT" muss der Artikel komplett überarbeitet werden
"""


class EditorAgent(BaseAgent):
    """
    Editor Agent für Qualitätsprüfung.
    Nutzt Claude Sonnet 4.5 oder Haiku 4.5.
    """
    
    def __init__(self, tier: Literal["premium", "budget"] = "premium"):
        super().__init__(
            name="Editor",
            system_prompt=EDITOR_SYSTEM_PROMPT,
            agent_type="editor",
            tier=tier,
            tools=["read_markdown"]
        )
    
    def review_article(
        self, 
        task: str,
        context: Dict[str, Any] = None
    ) -> Generator[AgentEvent, None, str]:
        """
        Prüft einen Wissensartikel.
        
        Args:
            task: Prüfauftrag
            context: Enthält article und core_question
        
        Yields:
            AgentEvents
        
        Returns:
            Editor-Feedback als Markdown
        """
        core_question = context.get("core_question", "") if context else ""
        article = context.get("article", "") if context else ""
        
        full_task = f"""## PRÜF-AUFTRAG

### KERNFRAGE (der Artikel muss diese beantworten!):
{core_question}

### Auftrag:
{task}

### ZU PRÜFENDER ARTIKEL:
{article[:10000] if article else "Kein Artikel vorhanden."}

## ANWEISUNGEN:
1. Lies den Artikel sorgfältig
2. Prüfe alle Qualitätskriterien
3. Gib konstruktives Feedback
4. Bewerte: GUT / VERBESSERUNGSWÜRDIG / MANGELHAFT

## JETZT: Prüfe den Artikel!"""

        result = ""
        for event in self.run(full_task, context):
            yield event
            if event.event_type == EventType.RESPONSE:
                result = event.content
        
        return result
