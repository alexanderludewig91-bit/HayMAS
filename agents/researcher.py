"""
HayMAS Researcher Agent

Single-Shot Researcher: Führt EINE Suchanfrage aus und gibt STRUKTURIERTE Ergebnisse zurück.
Der Orchestrator ruft den Researcher mehrfach auf für verschiedene Recherche-Runden.

NEU: Gibt JSON zurück statt Freitext-Zusammenfassung → 100% Quellenerhalt!

Unterstützt verschiedene Research-Tools:
- tavily_search: Allgemeine Websuche (kostenpflichtig)
- wikipedia_search: Enzyklopädisches Wissen (kostenlos)
- gnews_search: Aktuelle Nachrichten (kostenlos)
- hackernews_search: Tech-Diskussionen (kostenlos)
- semantic_scholar_search: Wissenschaftliche Paper (kostenlos)
"""

import json
import re
from typing import Dict, Any, List, Generator, Literal, Optional

from .base_agent import BaseAgent, AgentEvent, EventType


# Tool-spezifische Beschreibungen für den System-Prompt
TOOL_DESCRIPTIONS = {
    "tavily_search": "tavily_search - Durchsucht das Web nach aktuellen Informationen",
    "wikipedia_search": "wikipedia_search - Durchsucht Wikipedia nach Grundlagenwissen und Definitionen",
    "gnews_search": "gnews_search - Durchsucht Google News nach aktuellen Nachrichten",
    "hackernews_search": "hackernews_search - Durchsucht Hacker News nach Tech-Diskussionen und Meinungen",
    "semantic_scholar_search": "semantic_scholar_search - Durchsucht wissenschaftliche Paper und Forschungsarbeiten (200M+ Papers)",
    "arxiv_search": "arxiv_search - Durchsucht arXiv nach Preprints (ML, KI, Physik, Math, CS)",
    "ted_search": "ted_search - Durchsucht EU-Ausschreibungen und öffentliche Vergaben (TED)",
}


def get_researcher_prompt(tool_id: str) -> str:
    """Generiert den System-Prompt basierend auf dem ausgewählten Tool."""
    
    tool_name = f"{tool_id}_search" if not tool_id.endswith("_search") else tool_id
    tool_desc = TOOL_DESCRIPTIONS.get(tool_name, f"{tool_name} - Recherche-Tool")
    
    # Tool-spezifische Tipps
    tool_tips = {
        "tavily_search": """- Formuliere präzise Suchbegriffe
- Nutze Englisch für Tech-Themen
- Kombiniere mehrere relevante Keywords""",
        
        "wikipedia_search": """- Nutze Fachbegriffe und Eigennamen
- Suche nach Konzepten und Definitionen
- Bei Mehrdeutigkeit: Präzisiere den Begriff""",
        
        "gnews_search": """- Nutze aktuelle Begriffe und Namen
- Zeitraum beachten (period Parameter)
- Für deutsche News: language='de'""",
        
        "hackernews_search": """- Nutze englische Tech-Begriffe
- Suche nach Tool-Namen, Frameworks, Konzepten
- Hohe Punktzahl = Community-Relevanz""",
        
        "semantic_scholar_search": """- Nutze ENGLISCHE Fachbegriffe für beste Ergebnisse
- Suche nach spezifischen Konzepten, Methoden oder Forschungsfeldern
- Für aktuelle Forschung: year_from Parameter nutzen
- Zitationsanzahl zeigt Impact der Paper""",
        
        "arxiv_search": """- Nutze ENGLISCHE Fachbegriffe
- Besonders gut für: ML, KI, Computer Science, Physik, Mathematik
- Enthält neueste Preprints (oft vor offizieller Publikation)
- sort_by='date' für neueste Forschung""",
        
        "ted_search": """- Suche nach IT-Systemen, Software, Plattformen
- Gut für: Öffentliche Verwaltung, Behörden-IT, E-Government
- Optional: country='DE' für deutsche Ausschreibungen
- Enthält Auftraggeber, Werte und Beschreibungen""",
    }
    
    tips = tool_tips.get(tool_name, "- Formuliere präzise Suchbegriffe")
    
    return f"""Du bist ein Researcher-Agent für fokussierte Recherche.

## DEIN TOOL
{tool_desc}

## DEINE AUFGABE
Du führst EINE EINZIGE Suchanfrage aus und gibst die Ergebnisse als STRUKTURIERTES JSON zurück.

## REGELN
1. Nutze das {tool_name} Tool GENAU EINMAL
2. Wähle den besten Suchbegriff für die Aufgabe
3. Gib ALLE gefundenen Quellen als JSON zurück - KEINE geht verloren!
4. Extrahiere 2-3 Kernfakten pro Quelle
5. Bewerte die Relevanz jeder Quelle (1-5)

## TIPPS FÜR DIESES TOOL
{tips}

## OUTPUT-FORMAT (KRITISCH!)
Antworte NUR mit einem JSON-Objekt, KEIN anderer Text davor oder danach:

```json
{{
  "search_query": "dein verwendeter Suchbegriff",
  "tool": "{tool_name}",
  "sources": [
    {{
      "url": "https://example.com/article1",
      "title": "Titel der Quelle",
      "relevance": 5,
      "key_facts": [
        "Wichtiger Fakt 1 aus dieser Quelle",
        "Wichtiger Fakt 2 aus dieser Quelle"
      ]
    }},
    {{
      "url": "https://example.com/article2",
      "title": "Zweite Quelle",
      "relevance": 4,
      "key_facts": [
        "Fakt aus Quelle 2"
      ]
    }}
  ],
  "summary": "Ein Satz der alle Quellen zusammenfasst"
}}
```

## WICHTIG
- Gib NUR valides JSON zurück - kein Markdown, kein erklärender Text!
- ALLE Quellen aus dem Tool-Ergebnis müssen im JSON enthalten sein
- URLs müssen exakt übernommen werden (nicht kürzen oder ändern!)
- relevance: 5=sehr relevant, 1=wenig relevant
- key_facts: 2-3 Stichpunkte pro Quelle

## SPRACHE
- Suchbegriffe: Deutsch ODER Englisch (je nach Thema)
- key_facts und summary: Deutsch
"""


class ResearcherAgent(BaseAgent):
    """
    Researcher Agent für Single-Shot Recherche.
    Führt EINE Suche aus und gibt das Ergebnis zurück.
    
    Unterstützt verschiedene Research-Tools:
    - tavily: Allgemeine Websuche
    - wikipedia: Enzyklopädisches Wissen
    - gnews: Aktuelle Nachrichten
    - hackernews: Tech-Diskussionen
    """
    
    def __init__(
        self, 
        tier: Literal["premium", "budget"] = "premium",
        tool: str = "tavily"
    ):
        """
        Initialisiert den Researcher mit einem spezifischen Tool.
        
        Args:
            tier: "premium" oder "budget" Modell
            tool: Tool-ID (z.B. "tavily", "wikipedia", "gnews", "hackernews")
        """
        self.tool_id = tool
        tool_name = f"{tool}_search" if not tool.endswith("_search") else tool
        
        super().__init__(
            name="Researcher",
            system_prompt=get_researcher_prompt(tool),
            agent_type="researcher",
            tier=tier,
            tools=[tool_name]
        )
        
        self.current_tool = tool_name
    
    def set_tool(self, tool: str):
        """
        Wechselt das Research-Tool.
        
        Args:
            tool: Tool-ID (z.B. "tavily", "wikipedia")
        """
        self.tool_id = tool
        tool_name = f"{tool}_search" if not tool.endswith("_search") else tool
        self.current_tool = tool_name
        self.tools = [tool_name]
        self.system_prompt = get_researcher_prompt(tool)
    
    def get_available_tools(self) -> List[Dict]:
        """Überschreibt die Basis-Methode um spezifisches Tool zu verwenden."""
        return self.mcp_server.get_tools_for_agent(
            self.agent_type, 
            self.provider,
            specific_tools=[self.current_tool]
        )
    
    def research(
        self, 
        search_focus: str,
        context: Dict[str, Any] = None,
        tool: Optional[str] = None
    ) -> Generator[AgentEvent, None, str]:
        """
        Führt eine einzelne Recherche durch.
        
        Args:
            search_focus: Der spezifische Suchfokus (z.B. "Grundlagen", "Aktuelle News")
            context: Zusätzlicher Kontext (z.B. core_question)
            tool: Optional - Tool für diese Recherche (überschreibt Default)
        
        Yields:
            AgentEvents
        
        Returns:
            Strukturierte Recherche-Ergebnisse (als formatierter Text für den Writer)
        """
        # Tool wechseln falls angegeben
        if tool:
            self.set_tool(tool)
        
        core_question = ""
        if context and "core_question" in context:
            core_question = context["core_question"]
        
        task = f"""## RECHERCHE-AUFTRAG

### Kernfrage:
{core_question}

### Dein Fokus für diese Suche:
{search_focus}

### Anweisung:
1. Formuliere EINEN optimalen Suchbegriff
2. Führe EINE Suche mit {self.current_tool} aus
3. Gib das Ergebnis als JSON zurück (siehe System-Prompt für Format!)

WICHTIG: Antworte NUR mit JSON, kein anderer Text!"""

        result = ""
        raw_tool_results = None
        
        for event in self.run(task, context):
            yield event
            if event.event_type == EventType.RESPONSE:
                result = event.content
            # Tool-Ergebnisse erfassen für Fallback
            if event.event_type == EventType.TOOL_RESULT:
                raw_tool_results = event.data.get("result", {})
        
        # JSON parsen und in lesbares Format konvertieren
        parsed_result = self._parse_and_format_result(result, raw_tool_results)
        
        return parsed_result
    
    def _parse_and_format_result(self, llm_response: str, raw_tool_results: Dict = None) -> str:
        """
        Parst die JSON-Antwort des LLM und formatiert sie für den Writer.
        Falls JSON-Parsing fehlschlägt, nutzt die rohen Tool-Ergebnisse.
        
        Returns:
            Formatierter Markdown-Text mit allen Quellen
        """
        sources = []
        summary = ""
        search_query = ""
        
        # Versuche JSON aus der LLM-Antwort zu extrahieren
        try:
            # JSON aus Markdown-Block extrahieren falls vorhanden
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Versuche direkt als JSON zu parsen
                json_str = llm_response.strip()
            
            data = json.loads(json_str)
            sources = data.get("sources", [])
            summary = data.get("summary", "")
            search_query = data.get("search_query", "")
            
        except (json.JSONDecodeError, AttributeError):
            # JSON-Parsing fehlgeschlagen - nutze rohe Tool-Ergebnisse als Fallback
            if raw_tool_results and raw_tool_results.get("results"):
                sources = [
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", "Unbekannt"),
                        "relevance": 3,
                        "key_facts": [r.get("snippet", "")[:200]] if r.get("snippet") else []
                    }
                    for r in raw_tool_results["results"]
                ]
                search_query = raw_tool_results.get("query", "")
            else:
                # Letzter Fallback: LLM-Antwort direkt zurückgeben
                return llm_response
        
        # In lesbares Format für den Writer konvertieren
        output_lines = [
            f"## Recherche: {search_query}",
            f"**Tool:** {self.current_tool}",
            f"**Anzahl Quellen:** {len(sources)}",
            ""
        ]
        
        for i, source in enumerate(sources, 1):
            url = source.get("url", "")
            title = source.get("title", "Unbekannt")
            relevance = source.get("relevance", 3)
            key_facts = source.get("key_facts", [])
            
            output_lines.append(f"### [{i}] {title}")
            output_lines.append(f"- **URL:** {url}")
            output_lines.append(f"- **Relevanz:** {'⭐' * relevance}")
            
            if key_facts:
                output_lines.append("- **Kernfakten:**")
                for fact in key_facts:
                    output_lines.append(f"  - {fact}")
            
            output_lines.append("")
        
        if summary:
            output_lines.append("### Zusammenfassung")
            output_lines.append(summary)
        
        return "\n".join(output_lines)
