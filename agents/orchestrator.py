"""
HayMAS Orchestrator Agent

Koordiniert den Wissensartikel-Erstellungsprozess.
Dynamische Themenanalyse, adaptive Recherche-Runden und optionaler Editor-Review.
Mit integriertem Session-Logging.

NEU: Intelligente Tool- und Modell-Empfehlungen basierend auf Themenanalyse.
"""

from typing import Dict, Any, List, Generator, Optional, Literal
from dataclasses import dataclass, field, asdict
import json
import os
import glob

from .base_agent import BaseAgent, AgentEvent, EventType
from .editor import EditorVerdict, EditorIssue

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import OUTPUT_DIR, MAX_EDITOR_ITERATIONS, AGENT_MODELS
from session_logger import SessionLogger
from mcp_server.tools import get_all_tools, get_tools_for_topic, get_tools_description_for_prompt


# ============================================================================
# KONSTANTEN FÜR SMART EDITOR-ROUTING
# ============================================================================

# Maximale Anzahl an Nachrecherche-Runden nach Editor-Feedback
MAX_FOLLOWUP_RESEARCH_ROUNDS = 3

# Maximale Editor-Iterationen (um Endlosschleifen zu verhindern)
MAX_SMART_EDITOR_ITERATIONS = 2


ORCHESTRATOR_SYSTEM_PROMPT = """Du bist der Orchestrator eines Multi-Agenten-Systems zur Erstellung von Wissensartikeln.

## DEINE ROLLE
Du koordinierst den Workflow und steuerst die anderen Agenten.
Du selbst schreibst KEINE Inhalte - du delegierst an spezialisierte Agenten.

## SPRACHE
Alles auf Deutsch.
"""


TOPIC_ANALYSIS_PROMPT = """Analysiere die folgende Kernfrage und erstelle einen optimalen Recherche-Plan.

KERNFRAGE: {question}

VERFÜGBARE RESEARCH-TOOLS:
{tools_description}

Antworte NUR mit einem JSON-Objekt (keine Erklärungen, kein Markdown):

{{
  "topic_type": "tech|science|history|business|culture|current_events|general",
  "time_relevance": "current|recent|historical|timeless",
  "needs_current_data": true/false,
  "geographic_focus": "global|regional|local|none",
  "complexity": "simple|medium|complex",
  "recommended_rounds": [
    {{
      "name": "Kurzer Name der Runde",
      "focus": "Beschreibung was recherchiert werden soll",
      "search_query": "Konkrete Suchanfrage",
      "tool": "tavily|wikipedia|gnews|hackernews|semantic_scholar|arxiv|ted"
    }}
  ],
  "model_recommendations": {{
    "orchestrator": "premium|budget",
    "researcher": "premium|budget",
    "writer": "premium|budget",
    "editor": "premium|budget"
  }},
  "use_editor": true/false,
  "reasoning": "Kurze Begründung für die Strategie"
}}

## REGELN FÜR RECHERCHE-RUNDEN (WICHTIG!):

### Anzahl Runden nach Komplexität:
- "simple": 2-3 Runden (einfache Faktenfragen)
- "medium": 4-5 Runden (Standard-Recherche)
- "complex": 6-8 Runden (tiefgehende Analyse, Vergleiche, strategische Fragen)

### Tool-Auswahl (VERSCHIEDENE Tools nutzen!):
- wikipedia: Grundlagen, Definitionen, etabliertes Wissen (oft als 1. Runde)
- tavily: Aktuelle Web-Informationen, Fakten, Vergleiche
- gnews: Aktuelle Nachrichten, Pressemeldungen, Trends
- hackernews: Tech-Meinungen, Developer-Perspektiven, Tool-Bewertungen
- semantic_scholar: Wissenschaftliche Papers, Forschung, akademische Quellen
- arxiv: Preprints für ML, KI, Computer Science, Physik (neueste Forschung!)
- ted: EU-Ausschreibungen, öffentliche Vergaben, Behörden-IT

### Tool-Diversität ist PFLICHT:
- NIEMALS das gleiche Tool mehr als 2x hintereinander!
- Bei 6+ Runden: Mindestens 5 verschiedene Tools nutzen
- Kombiniere verschiedene Perspektiven: Fakten (tavily) + Meinungen (hackernews) + Grundlagen (wikipedia) + Forschung (semantic_scholar/arxiv)

### Empfohlene Muster nach Thementyp:
- Tech-Vergleiche: wikipedia → tavily → hackernews → gnews → tavily (deep-dive) → semantic_scholar
- Business/Strategie: wikipedia → gnews → tavily → tavily → hackernews
- Wissenschaft/KI: wikipedia → arxiv → semantic_scholar → tavily → arxiv → gnews
- Öffentliche Verwaltung/IT: wikipedia → ted → tavily → gnews → hackernews → ted → semantic_scholar
- Aktuelle Events: gnews → tavily → gnews → hackernews → wikipedia

## REGELN FÜR MODELL-EMPFEHLUNGEN:
- Bei "simple" Komplexität: Alle Agents auf "budget"
- Bei "medium" Komplexität: Writer auf "premium", Rest auf "budget"  
- Bei "complex" Komplexität: Writer + Editor auf "premium"
- use_editor nur bei komplexen oder sensiblen Themen auf true setzen
"""


@dataclass
class ResearchRound:
    """Eine einzelne Recherche-Runde"""
    name: str
    focus: str
    search_query: str
    tool: str = "tavily"  # NEU: Welches Tool für diese Runde
    enabled: bool = True


@dataclass
class ModelRecommendation:
    """Modell-Empfehlung für einen Agenten"""
    agent: str                    # orchestrator, researcher, writer, editor
    recommended_tier: str         # premium oder budget
    reasoning: str = ""           # Optional: Begründung


@dataclass
class ResearchPlan:
    """Der Recherche-Plan für einen Artikel"""
    topic_type: str
    time_relevance: str
    needs_current_data: bool
    geographic_focus: str
    complexity: str
    rounds: List[ResearchRound]
    use_editor: bool
    reasoning: str
    # NEU: Modell-Empfehlungen
    model_recommendations: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_type": self.topic_type,
            "time_relevance": self.time_relevance,
            "needs_current_data": self.needs_current_data,
            "geographic_focus": self.geographic_focus,
            "complexity": self.complexity,
            "rounds": [
                {
                    "name": r.name,
                    "focus": r.focus,
                    "search_query": r.search_query,
                    "tool": r.tool,
                    "enabled": r.enabled
                }
                for r in self.rounds
            ],
            "use_editor": self.use_editor,
            "reasoning": self.reasoning,
            "model_recommendations": self.model_recommendations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchPlan":
        # Unterstütze sowohl "rounds" als auch "recommended_rounds" (LLM-Variation)
        raw_rounds = data.get("rounds") or data.get("recommended_rounds", [])
        rounds = [
            ResearchRound(
                name=r.get("name", f"Runde {i+1}"),
                focus=r.get("focus", ""),
                search_query=r.get("search_query", r.get("focus", "")),
                tool=r.get("tool", "tavily"),  # Default: tavily
                enabled=r.get("enabled", True)
            )
            for i, r in enumerate(raw_rounds)
        ]
        
        # Modell-Empfehlungen parsen
        model_recs = data.get("model_recommendations", {})
        if not model_recs:
            # Fallback basierend auf Komplexität
            complexity = data.get("complexity", "medium")
            if complexity == "simple":
                model_recs = {"orchestrator": "budget", "researcher": "budget", "writer": "budget", "editor": "budget"}
            elif complexity == "complex":
                model_recs = {"orchestrator": "budget", "researcher": "budget", "writer": "premium", "editor": "premium"}
            else:  # medium
                model_recs = {"orchestrator": "budget", "researcher": "budget", "writer": "premium", "editor": "budget"}
        
        return cls(
            topic_type=data.get("topic_type", "general"),
            time_relevance=data.get("time_relevance", "timeless"),
            needs_current_data=data.get("needs_current_data", False),
            geographic_focus=data.get("geographic_focus", "global"),
            complexity=data.get("complexity", "medium"),
            rounds=rounds,
            use_editor=data.get("use_editor", False),
            reasoning=data.get("reasoning", ""),
            model_recommendations=model_recs
        )
    
    def get_estimated_cost(self) -> float:
        """
        Schätzt die Kosten basierend auf Modell-Empfehlungen.
        Grobe Schätzung in USD.
        """
        # Ungefähre Kosten pro Agent-Aufruf
        COST_ESTIMATES = {
            "orchestrator": {"premium": 0.05, "budget": 0.02},
            "researcher": {"premium": 0.03, "budget": 0.01},
            "writer": {"premium": 0.15, "budget": 0.08},
            "editor": {"premium": 0.05, "budget": 0.01},
        }
        
        total = 0.0
        active_rounds = len([r for r in self.rounds if r.enabled])
        
        # Orchestrator (1x)
        total += COST_ESTIMATES["orchestrator"].get(self.model_recommendations.get("orchestrator", "premium"), 0.03)
        
        # Researcher (pro Runde)
        total += active_rounds * COST_ESTIMATES["researcher"].get(self.model_recommendations.get("researcher", "premium"), 0.02)
        
        # Writer (1x, evtl. 2x bei Editor)
        writer_calls = 2 if self.use_editor else 1
        total += writer_calls * COST_ESTIMATES["writer"].get(self.model_recommendations.get("writer", "premium"), 0.10)
        
        # Editor (1x wenn aktiviert)
        if self.use_editor:
            total += COST_ESTIMATES["editor"].get(self.model_recommendations.get("editor", "premium"), 0.03)
        
        return round(total, 2)


# Fallback-Templates für den Fall dass die Analyse fehlschlägt
FALLBACK_TEMPLATES = [
    ("Grundlagen & Definitionen", "Recherchiere die GRUNDLAGEN zu: {q}. Was ist es? Wie funktioniert es?"),
    ("Aktuelle Entwicklungen", "Recherchiere AKTUELLE NEWS und TRENDS 2024/2025 zu: {q}."),
    ("Deep-Dive & Beispiele", "Recherchiere KONKRETE BEISPIELE und Details zu: {q}."),
]


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - koordiniert den gesamten Workflow.
    
    Unterstützt:
    - Intelligente Themenanalyse vor der Recherche
    - Dynamische, adaptive Recherche-Runden
    - Benutzerdefinierte Recherche-Pläne
    - Optionaler Editor-Review
    """
    
    def __init__(self, tier: Literal["premium", "budget"] = "premium"):
        super().__init__(
            name="Orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            agent_type="orchestrator",
            tier=tier,
            tools=[]
        )
        
        self.researcher = None
        self.writer = None
        self.editor = None
        self.logger: Optional[SessionLogger] = None
        
        self.research_results: List[str] = []
        self.article_result: Optional[str] = None
        self.editor_feedback: Optional[str] = None
        self.core_question: Optional[str] = None
    
    def set_agents(self, researcher: BaseAgent, writer: BaseAgent, editor: BaseAgent = None):
        """Setzt die Referenzen zu den anderen Agenten"""
        self.researcher = researcher
        self.writer = writer
        self.editor = editor
    
    # =========================================================================
    # SMART EDITOR-ROUTING METHODEN
    # =========================================================================
    
    def _evaluate_editor_feedback(self, verdict: EditorVerdict) -> Dict[str, Any]:
        """
        Entscheidet basierend auf Editor-Verdict, wie fortgefahren wird.
        
        Returns:
            {
                "action": "approved|revise|research",
                "research_rounds": [...],  # Falls action=research
                "reasoning": "..."
            }
        """
        # Wenn approved -> fertig
        if verdict.verdict == "approved":
            return {
                "action": "approved",
                "research_rounds": [],
                "reasoning": verdict.summary or "Artikel genehmigt"
            }
        
        # Prüfe ob Nachrecherche nötig
        content_gaps = [
            issue for issue in verdict.issues 
            if issue.type == "content_gap" and issue.suggested_action == "research"
        ]
        
        if content_gaps and verdict.verdict == "research":
            # Erstelle gezielte Recherche-Runden
            research_rounds = []
            for i, gap in enumerate(content_gaps[:MAX_FOLLOWUP_RESEARCH_ROUNDS]):
                # Tool basierend auf Gap-Typ wählen
                tool = self._select_tool_for_gap(gap)
                query = gap.research_query or gap.description
                research_rounds.append(ResearchRound(
                    name=f"Nachrecherche: {gap.description[:40]}...",
                    focus=gap.description,
                    search_query=query,
                    tool=tool,
                    enabled=True
                ))
            
            return {
                "action": "research",
                "research_rounds": research_rounds,
                "reasoning": f"{len(content_gaps)} inhaltliche Lücken gefunden, gezielte Nachrecherche"
            }
        
        # Default: Revision durch Writer
        return {
            "action": "revise",
            "research_rounds": [],
            "reasoning": verdict.summary or "Stilistische/strukturelle Verbesserungen nötig"
        }
    
    def _select_tool_for_gap(self, gap: EditorIssue) -> str:
        """Wählt das beste Tool für eine bestimmte Wissenslücke"""
        query_lower = (gap.research_query or gap.description).lower()
        
        # Heuristiken für Tool-Auswahl
        if any(kw in query_lower for kw in ["cost", "price", "pricing", "kosten", "lizenz", "preis"]):
            return "tavily"
        if any(kw in query_lower for kw in ["research", "study", "paper", "wissenschaft", "studie", "forschung"]):
            return "semantic_scholar"
        if any(kw in query_lower for kw in ["preprint", "arxiv", "ml", "machine learning", "neural", "ai model"]):
            return "arxiv"
        if any(kw in query_lower for kw in ["news", "aktuell", "2024", "2025", "2026", "trend"]):
            return "gnews"
        if any(kw in query_lower for kw in ["ausschreibung", "vergabe", "öffentlich", "behörde", "eu"]):
            return "ted"
        if any(kw in query_lower for kw in ["developer", "erfahrung", "review", "meinung", "community"]):
            return "hackernews"
        if any(kw in query_lower for kw in ["definition", "grundlage", "konzept", "was ist"]):
            return "wikipedia"
        
        return "tavily"  # Default
    
    def _run_followup_research(
        self, 
        rounds: List[ResearchRound],
        start_round_num: int,
        core_question: str
    ) -> Generator[AgentEvent, None, List[str]]:
        """
        Führt gezielte Nachrecherche-Runden durch.
        
        Args:
            rounds: Liste der Recherche-Runden
            start_round_num: Startnummer für die Runden-Bezeichnung
            core_question: Die ursprüngliche Kernfrage
            
        Yields:
            AgentEvents
            
        Returns:
            Liste der Recherche-Ergebnisse
        """
        results = []
        
        for i, round_config in enumerate(rounds):
            round_num = start_round_num + i
            
            # Tool-Icon für die Anzeige
            tool_icons = {
                "tavily": "🌐", "wikipedia": "📚", "gnews": "📰", 
                "hackernews": "🔶", "semantic_scholar": "🎓", 
                "arxiv": "📄", "ted": "🏛️"
            }
            tool_icon = tool_icons.get(round_config.tool, "🔍")
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"{tool_icon} Nachrecherche {i+1}/{len(rounds)}: {round_config.name} [{round_config.tool}]"
            )
            
            # Logging: Nachrecherche-Schritt starten
            step_idx = self.logger.start_step(
                agent="Researcher",
                model=self.researcher.model,
                provider=self.researcher.provider,
                tier=self.researcher.tier,
                action=f"followup_research_{i+1}",
                task=f"[{round_config.tool}] {round_config.search_query}"
            )
            
            # Researcher zurücksetzen und Tool setzen
            self.researcher.reset()
            self.researcher.set_tool(round_config.tool)
            
            # Researcher aufrufen
            result = ""
            tokens = None
            tool_calls = []
            
            context = {"core_question": core_question}
            
            for event in self.researcher.research(round_config.search_query, context):
                yield event
                if event.event_type == EventType.RESPONSE:
                    result = event.content
                if event.event_type == EventType.TOOL_CALL:
                    tool_calls.append(event.data.get("tool", "unknown"))
                if event.data.get("tokens"):
                    tokens = event.data["tokens"]
            
            # Logging: Schritt beenden
            if result and len(result) > 50:
                results.append(f"### Nachrecherche {i+1}: {round_config.name}\n\n{result}")
                self.logger.end_step(
                    step_idx,
                    status="success",
                    tokens=tokens,
                    tool_calls=tool_calls,
                    result_length=len(result)
                )
                yield AgentEvent(
                    event_type=EventType.STATUS,
                    agent_name=self.name,
                    content=f"✅ Nachrecherche {i+1} abgeschlossen: {len(result)} Zeichen"
                )
            else:
                self.logger.end_step(
                    step_idx,
                    status="error",
                    error="Keine ausreichenden Ergebnisse"
                )
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name=self.name,
                    content=f"⚠️ Nachrecherche {i+1} lieferte wenig Ergebnisse"
                )
        
        return results
    
    def analyze_topic(self, question: str) -> Generator[AgentEvent, None, ResearchPlan]:
        """
        Analysiert das Thema und erstellt einen optimalen Recherche-Plan.
        
        Yields Events für Live-Feedback, returns den fertigen Plan.
        Empfiehlt passende Tools und Modelle basierend auf Thementyp und Komplexität.
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="🔍 Analysiere Thema und erstelle Recherche-Plan..."
        )
        
        try:
            # Tool-Beschreibungen für den Prompt generieren
            tools_desc = get_tools_description_for_prompt()
            
            # LLM aufrufen für Themenanalyse
            prompt = TOPIC_ANALYSIS_PROMPT.format(
                question=question,
                tools_description=tools_desc
            )
            
            if self.provider == "anthropic":
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    system="Du bist ein Experte für Recherche-Strategien. Antworte NUR mit validem JSON.",
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.content[0].text
                
            elif self.provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Du bist ein Experte für Recherche-Strategien. Antworte NUR mit validem JSON."},
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = response.choices[0].message.content
                
            else:
                # Fallback für andere Provider
                response_text = None
            
            # JSON parsen
            if response_text:
                # Versuche JSON zu extrahieren (auch wenn in Markdown-Block)
                json_text = response_text.strip()
                if json_text.startswith("```"):
                    # Markdown-Code-Block entfernen
                    lines = json_text.split("\n")
                    json_text = "\n".join(lines[1:-1])
                
                plan_data = json.loads(json_text)
                plan = ResearchPlan.from_dict(plan_data)
                
                # Geschätzte Kosten berechnen
                estimated_cost = plan.get_estimated_cost()
                
                yield AgentEvent(
                    event_type=EventType.STATUS,
                    agent_name=self.name,
                    content=f"✅ Plan erstellt: {len(plan.rounds)} Runden, Editor: {'Ja' if plan.use_editor else 'Nein'}, ~${estimated_cost:.2f}",
                    data={
                        "plan": plan.to_dict(),
                        "estimated_cost": estimated_cost
                    }
                )
                
                return plan
                
        except Exception as e:
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name=self.name,
                content=f"⚠️ Themenanalyse fehlgeschlagen: {str(e)}. Verwende Standard-Plan."
            )
        
        # Fallback-Plan
        fallback_plan = ResearchPlan(
            topic_type="general",
            time_relevance="timeless",
            needs_current_data=True,
            geographic_focus="global",
            complexity="medium",
            rounds=[
                ResearchRound(
                    name=name,
                    focus=focus.format(q=question),
                    search_query=focus.format(q=question),
                    enabled=True
                )
                for name, focus in FALLBACK_TEMPLATES
            ],
            use_editor=False,
            reasoning="Fallback-Plan wegen Analysefehler"
        )
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"📋 Fallback-Plan: {len(fallback_plan.rounds)} Recherche-Runden",
            data={"plan": fallback_plan.to_dict()}
        )
        
        return fallback_plan
    
    def process_article(
        self, 
        core_question: str,
        plan: Optional[ResearchPlan] = None,
        # Legacy-Parameter für Rückwärtskompatibilität
        research_rounds: int = None,
        use_editor: bool = None,
        tiers: Dict[str, str] = None
    ) -> Generator[AgentEvent, None, Dict[str, Any]]:
        """
        Führt den Wissensartikel-Erstellungsprozess durch.
        
        Args:
            core_question: Die Kernfrage/Thema
            plan: Optional - ein ResearchPlan (vom User angepasst oder von analyze_topic())
            research_rounds: Legacy - Anzahl Runden (wird ignoriert wenn plan gegeben)
            use_editor: Legacy - Editor ja/nein (wird ignoriert wenn plan gegeben)
            tiers: Agent-Tiers (premium/budget)
        """
        self.reset()
        self.research_results = []
        self.article_result = None
        self.editor_feedback = None
        self.core_question = core_question
        
        # Wenn kein Plan gegeben, aber Legacy-Parameter, konvertieren
        if plan is None:
            if research_rounds is not None:
                # Legacy-Modus: Erstelle einfachen Plan aus Parametern
                research_rounds = max(1, min(5, research_rounds))
                plan = ResearchPlan(
                    topic_type="general",
                    time_relevance="timeless",
                    needs_current_data=True,
                    geographic_focus="global",
                    complexity="medium",
                    rounds=[
                        ResearchRound(
                            name=name,
                            focus=focus.format(q=core_question),
                            search_query=focus.format(q=core_question),
                            enabled=True
                        )
                        for name, focus in FALLBACK_TEMPLATES[:research_rounds]
                    ],
                    use_editor=use_editor if use_editor is not None else False,
                    reasoning="Legacy-Modus"
                )
            else:
                # Kein Plan und keine Legacy-Parameter: Analysiere Thema
                for event in self.analyze_topic(core_question):
                    yield event
                    if event.data and event.data.get("plan"):
                        plan = ResearchPlan.from_dict(event.data["plan"])
                
                # Falls Analyse fehlschlägt, Fallback
                if plan is None:
                    plan = ResearchPlan(
                        topic_type="general",
                        time_relevance="timeless",
                        needs_current_data=True,
                        geographic_focus="global",
                        complexity="medium",
                        rounds=[
                            ResearchRound(name=n, focus=f.format(q=core_question), search_query=f.format(q=core_question), enabled=True)
                            for n, f in FALLBACK_TEMPLATES
                        ],
                        use_editor=False,
                        reasoning="Fallback"
                    )
        
        # Nur aktivierte Runden verwenden
        active_rounds = [r for r in plan.rounds if r.enabled]
        
        # Logger initialisieren
        self.logger = SessionLogger(
            question=core_question,
            settings={
                "research_rounds": len(active_rounds),
                "use_editor": plan.use_editor,
                "tiers": tiers or {},
                "plan": plan.to_dict()
            }
        )
        
        try:
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"🚀 Starte Artikelerstellung ({len(active_rounds)} Recherche-Runden, Editor: {'Ja' if plan.use_editor else 'Nein'})"
            )
            
            # ===== PHASE 1: RECHERCHE (adaptive Runden aus Plan) =====
            for round_num, round_config in enumerate(active_rounds, 1):
                # Tool-Icon für die Anzeige
                tool_icons = {"tavily": "🌐", "wikipedia": "📚", "gnews": "📰", "hackernews": "🔶"}
                tool_icon = tool_icons.get(round_config.tool, "🔍")
                
                yield AgentEvent(
                    event_type=EventType.STATUS,
                    agent_name=self.name,
                    content=f"{tool_icon} Runde {round_num}/{len(active_rounds)}: {round_config.name} [{round_config.tool}]"
                )
                
                # Logging: Recherche-Schritt starten
                step_idx = self.logger.start_step(
                    agent="Researcher",
                    model=self.researcher.model,
                    provider=self.researcher.provider,
                    tier=self.researcher.tier,
                    action=f"research_round_{round_num}",
                    task=f"[{round_config.tool}] {round_config.search_query}"
                )
                
                # Researcher neu initialisieren für frischen Kontext!
                self.researcher.reset()
                
                # NEU: Tool für diese Runde setzen
                self.researcher.set_tool(round_config.tool)
                
                # Researcher aufrufen mit der spezifischen Suchanfrage
                result = ""
                tokens = None
                tool_calls = []
                
                context = {"core_question": core_question}
                
                for event in self.researcher.research(round_config.search_query, context):
                    yield event
                    if event.event_type == EventType.RESPONSE:
                        result = event.content
                    if event.event_type == EventType.TOOL_CALL:
                        tool_calls.append(event.data.get("tool", "unknown"))
                    if event.data.get("tokens"):
                        tokens = event.data["tokens"]
                
                # Logging: Recherche-Schritt beenden
                if result and len(result) > 50:
                    self.research_results.append(f"### Runde {round_num}: {round_config.name}\n\n{result}")
                    self.logger.end_step(
                        step_idx,
                        status="success",
                        tokens=tokens,
                        tool_calls=tool_calls,
                        result_length=len(result)
                    )
                    yield AgentEvent(
                        event_type=EventType.STATUS,
                        agent_name=self.name,
                        content=f"✅ Runde {round_num} abgeschlossen: {len(result)} Zeichen"
                    )
                else:
                    self.logger.end_step(
                        step_idx,
                        status="error",
                        error="Keine ausreichenden Ergebnisse"
                    )
                    yield AgentEvent(
                        event_type=EventType.ERROR,
                        agent_name=self.name,
                        content=f"⚠️ Runde {round_num} lieferte wenig Ergebnisse"
                    )
            
            # Recherche-Ergebnisse zusammenführen
            all_research = "\n\n---\n\n".join(self.research_results)
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"📚 Recherche abgeschlossen: {len(all_research)} Zeichen aus {len(self.research_results)} Runden"
            )
            
            # ===== PHASE 2: ARTIKEL SCHREIBEN =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content="✍️ Writer erstellt Artikel..."
            )
            
            # Logging: Writer-Schritt starten
            writer_step = self.logger.start_step(
                agent="Writer",
                model=self.writer.model,
                provider=self.writer.provider,
                tier=self.writer.tier,
                action="write_article",
                task=f"Erstelle Wissensartikel zu: {core_question}"
            )
            
            self.writer.reset()
            
            writer_context = {
                "core_question": core_question,
                "research_results": all_research
            }
            
            writer_task = f"""Erstelle einen umfassenden Wissensartikel zur Kernfrage: {core_question}

## WICHTIGE REGELN FÜR QUELLEN:

1. **ZITIERE ALLE Quellen im Text mit Nummern!**
   - Format: [1], [2], [3], etc.
   - JEDE Quelle aus der Recherche sollte mindestens einmal zitiert werden
   - Die Quellen sind bereits nummeriert (z.B. "[1] Titel")

2. **QUELLENVERZEICHNIS am Ende ist PFLICHT!**
   - Liste ALLE Quellen mit ihrer Nummer und URL
   - Format: 
     ```
     ## Quellen
     - [1] Titel der Quelle - URL
     - [2] Zweite Quelle - URL
     ```

3. **NUTZE ALLE bereitgestellten Quellen!**
   - Die Recherche hat pro Runde mehrere Quellen mit URLs geliefert
   - Ziel: ALLE Quellen im Artikel verwenden (typischerweise 15-25)
   - Die URLs stehen bei jeder Quelle unter "URL:"

## STRUKTUR:
- Der Artikel sollte mindestens 2000 Wörter haben
- Gut strukturiert mit Überschriften (##, ###)
- Am Ende: Vollständiges Quellenverzeichnis

## HINWEIS:
Die Recherche-Ergebnisse sind STRUKTURIERT:
- Jede Quelle hat: Titel, URL, Relevanz, Kernfakten
- Übernimm die URLs EXAKT ins Quellenverzeichnis
- Nummerierung fortlaufend über alle Recherche-Runden"""

            article = ""
            writer_tokens = None
            for event in self.writer.run(writer_task, writer_context):
                yield event
                if event.event_type == EventType.RESPONSE:
                    article = event.content
                if event.data.get("tokens"):
                    writer_tokens = event.data["tokens"]
            
            self.article_result = article
            
            # Logging: Writer-Schritt beenden
            self.logger.end_step(
                writer_step,
                status="success" if article else "error",
                tokens=writer_tokens,
                result_length=len(article)
            )
            
            # ===== PHASE 3: SMART EDITOR REVIEW (wenn aktiviert im Plan) =====
            if plan.use_editor and self.editor:
                editor_iteration = 0
                current_research = all_research
                
                while editor_iteration < MAX_SMART_EDITOR_ITERATIONS:
                    editor_iteration += 1
                    
                    yield AgentEvent(
                        event_type=EventType.STATUS,
                        agent_name=self.name,
                        content=f"📝 Editor prüft Artikel (Iteration {editor_iteration})..."
                    )
                    
                    # Logging: Editor-Schritt starten
                    editor_step = self.logger.start_step(
                        agent="Editor",
                        model=self.editor.model,
                        provider=self.editor.provider,
                        tier=self.editor.tier,
                        action=f"review_iteration_{editor_iteration}",
                        task="Prüfe Artikel auf Qualität"
                    )
                    
                    self.editor.reset()
                    
                    editor_context = {
                        "core_question": core_question,
                        "article": article
                    }
                    
                    editor_task = f"""Prüfe den folgenden Wissensartikel auf Qualität:

1. Ist der Artikel relevant zur Kernfrage?
2. Ist er gut strukturiert?
3. Sind die Informationen korrekt und vollständig?
4. Gibt es Verbesserungsvorschläge?

Gib konstruktives Feedback und VERGISS NICHT das strukturierte JSON am Ende!"""

                    editor_feedback = ""
                    editor_tokens = None
                    for event in self.editor.run(editor_task, editor_context):
                        yield event
                        if event.event_type == EventType.RESPONSE:
                            editor_feedback = event.content
                        if event.data.get("tokens"):
                            editor_tokens = event.data["tokens"]
                    
                    self.editor_feedback = editor_feedback
                    
                    # Logging: Editor-Schritt beenden
                    self.logger.end_step(
                        editor_step,
                        status="success",
                        tokens=editor_tokens,
                        result_length=len(editor_feedback)
                    )
                    
                    # NEU: Strukturiertes Verdict parsen
                    verdict = EditorVerdict.from_response(editor_feedback)
                    
                    yield AgentEvent(
                        event_type=EventType.STATUS,
                        agent_name=self.name,
                        content=f"🔍 Editor-Verdict: {verdict.verdict.upper()} (Konfidenz: {verdict.confidence:.0%}, {len(verdict.issues)} Issues)",
                        data={
                            "verdict": verdict.to_dict(),
                            "iteration": editor_iteration
                        }
                    )
                    
                    # Logging: Editor-Entscheidung
                    self.logger.log_event({
                        "type": "editor_verdict",
                        "iteration": editor_iteration,
                        "verdict": verdict.verdict,
                        "confidence": verdict.confidence,
                        "issues_count": len(verdict.issues),
                        "has_content_gaps": verdict.has_content_gaps()
                    })
                    
                    # NEU: Orchestrator entscheidet basierend auf Verdict
                    decision = self._evaluate_editor_feedback(verdict)
                    
                    yield AgentEvent(
                        event_type=EventType.STATUS,
                        agent_name=self.name,
                        content=f"🎯 Orchestrator-Entscheidung: {decision['action'].upper()} - {decision['reasoning']}"
                    )
                    
                    # ========== ACTION: APPROVED ==========
                    if decision["action"] == "approved":
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name=self.name,
                            content="✅ Artikel vom Editor genehmigt!"
                        )
                        break  # Fertig!
                    
                    # ========== ACTION: RESEARCH ==========
                    elif decision["action"] == "research" and decision["research_rounds"]:
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name=self.name,
                            content=f"🔍 Starte Nachrecherche: {len(decision['research_rounds'])} gezielte Runden"
                        )
                        
                        # Gezielte Nachrecherche durchführen
                        followup_results = []
                        for event_or_result in self._run_followup_research(
                            decision["research_rounds"],
                            start_round_num=len(active_rounds) + 1,
                            core_question=core_question
                        ):
                            if isinstance(event_or_result, AgentEvent):
                                yield event_or_result
                            elif isinstance(event_or_result, list):
                                followup_results = event_or_result
                        
                        # Erweiterte Recherche-Ergebnisse zusammenführen
                        if followup_results:
                            additional_research = "\n\n---\n\n## Nachrecherche (Editor-Anforderung)\n\n" + "\n\n".join(followup_results)
                            current_research = all_research + additional_research
                            self.research_results.extend(followup_results)
                        
                        # Writer mit erweitertem Kontext aufrufen
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name=self.name,
                            content="✍️ Writer überarbeitet Artikel mit Nachrecherche-Ergebnissen..."
                        )
                        
                        # Logging: Revision mit Nachrecherche
                        revision_step = self.logger.start_step(
                            agent="Writer",
                            model=self.writer.model,
                            provider=self.writer.provider,
                            tier=self.writer.tier,
                            action=f"revision_with_research_{editor_iteration}",
                            task="Überarbeite Artikel mit Nachrecherche-Ergebnissen"
                        )
                        
                        self.writer.reset()
                        
                        revision_context = {
                            "core_question": core_question,
                            "research_results": current_research,
                            "editor_feedback": editor_feedback,
                            "original_article": article
                        }
                        
                        revision_task = f"""Überarbeite den Artikel basierend auf dem Editor-Feedback UND den neuen Recherche-Ergebnissen.

Editor-Feedback:
{editor_feedback}

NEUE Recherche-Ergebnisse (nutze diese zur Behebung der Wissenslücken!):
{additional_research if followup_results else "(keine neuen Ergebnisse)"}

Verbessere den Artikel entsprechend und integriere die neuen Informationen."""

                        revision_tokens = None
                        for event in self.writer.run(revision_task, revision_context):
                            yield event
                            if event.event_type == EventType.RESPONSE:
                                article = event.content
                            if event.data.get("tokens"):
                                revision_tokens = event.data["tokens"]
                        
                        self.article_result = article
                        
                        self.logger.end_step(
                            revision_step,
                            status="success",
                            tokens=revision_tokens,
                            result_length=len(article)
                        )
                    
                    # ========== ACTION: REVISE ==========
                    else:  # "revise" - nur stilistische/strukturelle Änderungen
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name=self.name,
                            content="✍️ Writer überarbeitet Artikel (keine Nachrecherche nötig)..."
                        )
                        
                        # Logging: Revision-Schritt starten
                        revision_step = self.logger.start_step(
                            agent="Writer",
                            model=self.writer.model,
                            provider=self.writer.provider,
                            tier=self.writer.tier,
                            action=f"revision_{editor_iteration}",
                            task="Überarbeite Artikel basierend auf Editor-Feedback"
                        )
                        
                        self.writer.reset()
                        
                        revision_context = {
                            "core_question": core_question,
                            "research_results": current_research,
                            "editor_feedback": editor_feedback,
                            "original_article": article
                        }
                        
                        revision_task = f"""Überarbeite den Artikel basierend auf dem Editor-Feedback.

Editor-Feedback:
{editor_feedback}

Verbessere den Artikel entsprechend."""

                        revision_tokens = None
                        for event in self.writer.run(revision_task, revision_context):
                            yield event
                            if event.event_type == EventType.RESPONSE:
                                article = event.content
                            if event.data.get("tokens"):
                                revision_tokens = event.data["tokens"]
                        
                        self.article_result = article
                        
                        # Logging: Revision-Schritt beenden
                        self.logger.end_step(
                            revision_step,
                            status="success",
                            tokens=revision_tokens,
                            result_length=len(article)
                        )
                        
                        # Nach "revise" beenden wir den Loop (keine weitere Editor-Iteration)
                        break
                
                # Warnung wenn Max-Iterationen erreicht
                if editor_iteration >= MAX_SMART_EDITOR_ITERATIONS:
                    yield AgentEvent(
                        event_type=EventType.STATUS,
                        agent_name=self.name,
                        content=f"⚠️ Max. Editor-Iterationen ({MAX_SMART_EDITOR_ITERATIONS}) erreicht, finalisiere Artikel..."
                    )
            
            # ===== PHASE 4: SPEICHERN & FERTIG =====
            article_path = self._save_article(article)
            article_words = len(article.split())
            
            # Logging: Session abschließen
            self.logger.complete(
                article_path=article_path,
                article_words=article_words
            )
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"💾 Artikel gespeichert: {os.path.basename(article_path)}"
            )
            
            yield AgentEvent(
                event_type=EventType.RESPONSE,
                agent_name=self.name,
                content=f"✅ Wissensartikel erfolgreich erstellt!",
                data={
                    "article_path": article_path,
                    "research_rounds": len(self.research_results),
                    "article_length": len(article),
                    "editor_used": plan.use_editor and self.editor is not None,
                    "log_file": self.logger.get_log_filename()
                }
            )
            
            return {
                "success": True,
                "article_path": article_path,
                "log_file": self.logger.get_log_filename(),
                "summary": f"Artikel mit {len(article)} Zeichen aus {len(self.research_results)} Recherche-Runden erstellt."
            }
            
        except Exception as e:
            # Bei Fehler: Logger informieren
            if self.logger:
                self.logger.error(str(e))
            raise
    
    def abort(self):
        """Bricht die Generierung ab"""
        if self.logger:
            self.logger.abort("User cancelled")
    
    def _save_article(self, content: str) -> str:
        """Speichert den Artikel als Markdown-Datei"""
        from datetime import datetime
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in self.core_question[:50])
        safe_name = safe_name.strip().replace(" ", "_").lower()
        
        # WICHTIG: Timestamp muss mit Logger übereinstimmen!
        timestamp = self.logger.session_id if self.logger else datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.md"
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
