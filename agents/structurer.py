"""
HayMAS Struktur Agent

Erstellt die Folien-Struktur aus Recherche-Ergebnissen.
Nutzt GPT-4o für kreatives Schreiben.
"""

from typing import Dict, Any, List, Generator
import json

from .base_agent import BaseAgent, AgentEvent, EventType

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import STRUCTURER_MODEL, STRUCTURER_PROVIDER


STRUCTURER_SYSTEM_PROMPT = """Du erstellst INHALTSREICHE Präsentationen. Jede Folie muss OHNE Sprecher vollständig verständlich sein.

## DEIN TOOL
`save_markdown` - Speichere die Präsentation damit.

## ABSOLUT INAKZEPTABEL - SO NICHT!

Diese Folien sind WERTLOS und werden ABGELEHNT:

```
# Folie 3: Einführung in ServiceNow's KI-Plattform
- "Agentic AI": Autonome Softwareagenten
- Integration von maschinellem Lernen
```
WARUM SCHLECHT? Nur 2 Stichworte ohne jede Erklärung. Das sind Überschriften, keine Inhalte!

```
# Folie 5: Funktionen des Building Agents
- Kategorisierung von Vorfällen
- Nutzung von Wissensdokumenten
- Automatisierte Lösung
```
WARUM SCHLECHT? Nur Schlagworte! Was bedeutet das konkret? Wie funktioniert es? Für wen?

## SO MUSS ES AUSSEHEN - RICHTIG:

```
# Folie 3: Was ist ServiceNow's KI-Plattform?
- ServiceNow integriert KI direkt in seine Workflow-Plattform, sodass Unternehmen 
  IT-Service, HR und Kundenservice automatisieren können
- "Agentic AI" bezeichnet autonome Software-Agenten, die selbstständig Aufgaben 
  erledigen - z.B. Tickets kategorisieren, Antworten vorschlagen, Prozesse starten
- Die KI nutzt maschinelles Lernen um aus historischen Daten zu lernen: Je mehr 
  Tickets bearbeitet werden, desto besser werden die Vorhersagen
- Natürliche Sprachverarbeitung (NLP) ermöglicht es Nutzern, in normaler Sprache 
  mit dem System zu interagieren statt komplizierte Formulare auszufüllen
- Zielgruppe: IT-Teams, HR-Abteilungen und Kundenservice-Center die ihre 
  Prozesse beschleunigen wollen
```

```
# Folie 5: Kernfunktionen des Building Agents im Detail
- Automatische Ticket-Kategorisierung: Der Agent analysiert eingehende Anfragen 
  per NLP und ordnet sie automatisch der richtigen Kategorie und Priorität zu
- Intelligente Zuweisung: Basierend auf Verfügbarkeit, Expertise und Workload 
  wird das Ticket dem am besten geeigneten Mitarbeiter zugewiesen
- Wissensbasierte Lösungsvorschläge: Der Agent durchsucht die Wissensdatenbank 
  und schlägt passende Artikel oder Lösungen vor - inklusive Erfolgswahrscheinlichkeit
- Automatische Eskalation: Bei kritischen Vorfällen oder Zeitüberschreitungen 
  eskaliert der Agent selbstständig nach definierten Regeln
- Self-Service-Unterstützung: Für Standardanfragen kann der Agent vollautomatisch 
  antworten und Prozesse auslösen (z.B. Passwort zurücksetzen)
```

## REGELN FÜR JEDEN STICHPUNKT

Jeder einzelne Stichpunkt muss:
1. Einen VOLLSTÄNDIGEN Gedanken enthalten (nicht nur ein Stichwort!)
2. ERKLÄREN was gemeint ist (nicht nur benennen!)
3. KONTEXT geben (warum ist das relevant? für wen? wie funktioniert es?)

FALSCH: "- Automatisierung von Prozessen"
RICHTIG: "- Die Automatisierung reduziert manuelle Arbeit bei Routineaufgaben wie 
          Ticket-Erstellung, Status-Updates und Benachrichtigungen um ca. 70%"

## MINDESTANFORDERUNGEN PRO FOLIE

- Titelfolie: Titel + aussagekräftiger Untertitel
- Inhaltsfolien: MINDESTENS 4 ausführliche Stichpunkte
- Jeder Stichpunkt: MINDESTENS 15-25 Wörter (ein vollständiger Satz/Gedanke!)
- Komplexe Themen: 5-6 Punkte mit mehr Detail

## STRUKTUR DER PRÄSENTATION

1. Titel + Einleitung (2 Folien): Kontext setzen, Relevanz erklären
2. Grundlagen (2-3 Folien): Begriffe erklären, Konzepte einführen
3. KERNTHEMA (5-7 Folien): Hier liegt der Fokus - ausführlich und detailliert!
4. Praxisbeispiele (2 Folien): Konkrete Anwendungsfälle mit Zahlen wenn möglich
5. Fazit (1-2 Folien): Zusammenfassung der Kernerkenntnisse

## QUALITÄTSPRÜFUNG VOR DEM SPEICHERN

Prüfe JEDE Folie:
- Hat die Folie mindestens 4 Stichpunkte? (außer Titel/Fazit)
- Ist jeder Stichpunkt ein vollständiger Gedanke mit Erklärung?
- Würde jemand der das Thema nicht kennt die Folie verstehen?

Wenn NEIN → Überarbeite die Folie bevor du speicherst!

## Nach dem Erstellen
SPEICHERE mit `save_markdown`!
"""


class StructurerAgent(BaseAgent):
    """
    Struktur Agent - erstellt Folien-Strukturen aus Recherche-Ergebnissen.
    
    Dieser Agent:
    - Nutzt GPT-4o für kreatives Schreiben
    - Erstellt prägnante, präsentationsgerechte Texte
    - Strukturiert Inhalte logisch
    - Speichert die Markdown-Struktur
    """
    
    def __init__(self):
        super().__init__(
            name="Struktur-Agent",
            system_prompt=STRUCTURER_SYSTEM_PROMPT,
            provider=STRUCTURER_PROVIDER,
            model=STRUCTURER_MODEL,
            tools=["save_markdown", "read_markdown"]
        )
    
    def _get_agent_type(self) -> str:
        return "structurer"
    
    def create_structure(
        self,
        research_results: str,
        outline: str = None,
        context: Dict[str, Any] = None
    ) -> Generator[AgentEvent, None, str]:
        """
        Erstellt eine Folien-Struktur aus Recherche-Ergebnissen.
        
        Args:
            research_results: Die Recherche-Ergebnisse
            outline: Optional - Grobe Gliederungsvorgabe
            context: Optional - zusätzlicher Kontext (z.B. Zielgruppe)
        
        Yields:
            AgentEvents für Live-Updates
        
        Returns:
            Die Markdown-Folienstruktur als String
        """
        self.reset()
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="Erstelle Folien-Struktur aus Recherche-Ergebnissen..."
        )
        
        # Auftrag formulieren
        task = f"""Erstelle eine Präsentationsstruktur basierend auf den folgenden Recherche-Ergebnissen:

## RECHERCHE-ERGEBNISSE:
{research_results}

"""
        
        if outline:
            task += f"""
## GLIEDERUNGSVORGABE:
{outline}

"""
        
        task += """## AUFTRAG:
1. Analysiere die Recherche-Ergebnisse
2. Erstelle 10-15 Folien mit klarer Struktur
3. Nutze prägnante Bullet Points
4. Speichere das Ergebnis mit dem save_markdown Tool
5. Gib die fertige Struktur zurück

Beginne jetzt mit der Erstellung der Folien-Struktur."""

        # Context erweitern
        full_context = context or {}
        
        # ReAct Loop ausführen
        result = ""
        for event in self.run(task, full_context):
            yield event
            
            if event.event_type == EventType.RESPONSE:
                result = event.content
        
        return result
    
    def revise_structure(
        self,
        current_structure: str,
        feedback: str
    ) -> Generator[AgentEvent, None, str]:
        """
        Überarbeitet eine bestehende Struktur basierend auf Feedback.
        
        Args:
            current_structure: Die aktuelle Folien-Struktur
            feedback: Feedback zur Überarbeitung
        
        Yields:
            AgentEvents für Live-Updates
        
        Returns:
            Die überarbeitete Markdown-Folienstruktur
        """
        self.reset()
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="Überarbeite Folien-Struktur basierend auf Feedback..."
        )
        
        task = f"""Überarbeite die folgende Präsentationsstruktur basierend auf dem Feedback:

## AKTUELLE STRUKTUR:
{current_structure}

## FEEDBACK:
{feedback}

## AUFTRAG:
1. Setze das Feedback um
2. Behalte die guten Teile bei
3. Verbessere die kritisierten Punkte
4. Speichere die überarbeitete Version mit save_markdown
5. Gib die finale Struktur zurück

Beginne mit der Überarbeitung."""

        result = ""
        for event in self.run(task):
            yield event
            
            if event.event_type == EventType.RESPONSE:
                result = event.content
        
        return result
