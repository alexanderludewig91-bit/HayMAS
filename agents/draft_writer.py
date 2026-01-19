"""
HayMAS Draft Writer Agent

Phase 1 des "Verified Deep Thinking" Ansatzes:
Erstellt einen intelligenten Artikel-Entwurf mit dem EIGENEN WISSEN des LLM.

WICHTIG: Der Draft Writer markiert explizit:
- [FACT-CHECK: ...] - Fakten die verifiziert werden sollten
- [UNSICHER: ...] - Stellen wo das LLM unsicher ist  
- [RECHERCHE: ...] - Themen die recherchiert werden müssen
- [QUELLE: ...] - Aussagen die eine Quelle brauchen

Diese Markierungen werden dann vom Researcher gezielt abgearbeitet.
"""

from typing import Dict, Any, Generator, Literal, List
from .base_agent import BaseAgent, AgentEvent, EventType


DRAFT_WRITER_PROMPT = """Du bist ein Experten-Autor für Wissensartikel.

## DEINE AUFGABE
Schreibe einen umfassenden, tiefgehenden Artikel-ENTWURF zu dem gegebenen Thema.
Nutze dabei DEIN GESAMTES WISSEN - du hast Zugriff auf enormes Fachwissen aus deinem Training.

## KRITISCH: MARKIERUNGEN SETZEN
Während du schreibst, markiere folgende Stellen im Text:

1. **[FACT-CHECK: "exakte Aussage"]** 
   - Für konkrete Fakten (Zahlen, Daten, Namen)
   - Beispiel: Das Unternehmen wurde [FACT-CHECK: "2004 gegründet"].

2. **[UNSICHER: "Thema"]**
   - Für Stellen wo du dir nicht 100% sicher bist
   - Beispiel: Die Technologie basiert [UNSICHER: "möglicherweise auf Transformer-Architektur"].

3. **[RECHERCHE: "Suchbegriff"]**
   - Für aktuelle Informationen die du nicht haben kannst
   - Beispiel: [RECHERCHE: "ServiceNow Build Agent Release 2024"]

4. **[QUELLE: "Kernaussage"]**
   - Für wichtige Aussagen die eine Quellenangabe brauchen
   - Beispiel: [QUELLE: "Low-Code reduziert Entwicklungszeit um 70%"]

## ARTIKEL-STRUKTUR
1. **Management Summary** (5-7 Sätze)
2. **Einleitung & Kontext** (warum ist das Thema relevant?)
3. **Grundlagen & Konzepte** (tiefgehende Erklärungen)
4. **Aktuelle Entwicklungen** (mit [RECHERCHE:] Markierungen)
5. **Praxisbeispiele / Use Cases** (konkret und anwendungsnah)
6. **Kritische Einordnung** (Vor-/Nachteile, Limitationen)
7. **Fazit & Ausblick**

## QUALITÄTSANFORDERUNGEN
- Expertenniveau: Schreibe für Fachleute, nicht für Anfänger
- Tiefe: Erkläre Zusammenhänge, nicht nur Oberfläche
- Konkret: Nenne konkrete Beispiele, Tools, Methoden
- Kritisch: Zeige auch Grenzen und Herausforderungen
- Umfangreich: Mindestens 2000 Wörter, eher mehr

## SPRACHE
- Deutsch
- Fachbegriffe erklären aber nicht vermeiden
- Sachlicher, wissenschaftlicher Stil

## WICHTIG
- Nutze WIRKLICH dein Wissen - du weißt mehr als du denkst!
- Setze Markierungen wo nötig, aber nicht übertrieben
- Ein guter Entwurf hat ca. 10-20 Markierungen verteilt im Text
- Schreibe VOLLSTÄNDIG, nicht nur Stichpunkte
"""


class DraftWriterAgent(BaseAgent):
    """
    Draft Writer Agent für Phase 1 des Verified Deep Thinking Flows.
    
    Erstellt einen umfassenden Artikel-Entwurf basierend auf dem 
    Wissen des LLM, mit expliziten Markierungen für:
    - Fakten die verifiziert werden müssen
    - Unsichere Stellen
    - Themen die recherchiert werden müssen
    - Aussagen die Quellen brauchen
    """
    
    def __init__(self, tier: Literal["premium", "budget"] = "premium"):
        # Nutze GPT-5.2 für beste Wissenstiefe
        super().__init__(
            name="DraftWriter",
            system_prompt=DRAFT_WRITER_PROMPT,
            agent_type="writer",  # Nutzt Writer-Modell-Config
            tier=tier,
            tools=[]  # Keine Tools - nutzt nur eigenes Wissen!
        )
    
    def create_draft(
        self, 
        question: str,
        additional_context: str = ""
    ) -> Generator[AgentEvent, None, str]:
        """
        Erstellt einen Artikel-Entwurf mit Markierungen.
        
        Args:
            question: Die Kernfrage / das Thema
            additional_context: Optionaler zusätzlicher Kontext
        
        Yields:
            AgentEvents während der Generierung
        
        Returns:
            Artikel-Entwurf mit [FACT-CHECK], [RECHERCHE], etc. Markierungen
        """
        task = f"""## ARTIKEL-AUFTRAG

### Kernfrage / Thema:
{question}

"""
        if additional_context:
            task += f"""### Zusätzlicher Kontext:
{additional_context}

"""
        
        task += """### Anweisung:
Schreibe jetzt einen umfassenden, tiefgehenden Artikel-Entwurf.
Nutze DEIN GESAMTES WISSEN zu diesem Thema.
Setze die Markierungen ([FACT-CHECK:], [RECHERCHE:], etc.) wo nötig.

BEGINNE JETZT MIT DEM ARTIKEL:"""

        result = ""
        for event in self.run(task):
            yield event
            if event.event_type == EventType.RESPONSE:
                result = event.content
        
        return result
    
    def extract_markers(self, draft: str) -> Dict[str, List[str]]:
        """
        Extrahiert alle Markierungen aus dem Entwurf.
        
        Returns:
            Dict mit Listen pro Markierungstyp:
            {
                "fact_check": ["Aussage 1", "Aussage 2"],
                "unsicher": ["Thema 1"],
                "recherche": ["Suchbegriff 1", "Suchbegriff 2"],
                "quelle": ["Kernaussage 1"]
            }
        """
        import re
        
        markers = {
            "fact_check": [],
            "unsicher": [],
            "recherche": [],
            "quelle": []
        }
        
        # Pattern für verschiedene Markierungen
        patterns = {
            "fact_check": r'\[FACT-CHECK:\s*["\']?([^"\'\]]+)["\']?\]',
            "unsicher": r'\[UNSICHER:\s*["\']?([^"\'\]]+)["\']?\]',
            "recherche": r'\[RECHERCHE:\s*["\']?([^"\'\]]+)["\']?\]',
            "quelle": r'\[QUELLE:\s*["\']?([^"\'\]]+)["\']?\]',
        }
        
        for marker_type, pattern in patterns.items():
            matches = re.findall(pattern, draft, re.IGNORECASE)
            markers[marker_type] = [m.strip() for m in matches]
        
        return markers
    
    def count_markers(self, draft: str) -> Dict[str, int]:
        """Zählt die Anzahl jeder Markierungsart."""
        markers = self.extract_markers(draft)
        return {k: len(v) for k, v in markers.items()}
