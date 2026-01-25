"""
Evidence-Gated Orchestrator

Koordiniert den gesamten Evidence-Gated Workflow.
Mit vollständigem Step-Logging und dynamischer Modellauswahl.
"""

import os
import json
import re
from typing import Dict, Any, Generator, Optional, List
from datetime import datetime, date

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.base_agent import AgentEvent, EventType, BaseAgent
from session_logger import SessionLogger
from config import OUTPUT_DIR, AGENT_MODELS, AVAILABLE_MODELS, get_model_for_agent
from mcp_server.server import get_mcp_server

from .models import (
    ClaimRegister, EvidencePack, ReviewReport, ClaimStatus,
    QuestionBrief, TermMap, Outline, OutlineSection,
    Claim, ClaimType, EvidenceClass, SourceClass, RetrievalTicket,
    Source, SourceRating
)


class EvidenceGatedOrchestrator:
    """
    Orchestriert den Evidence-Gated Workflow.
    
    Mit dynamischer Modellauswahl basierend auf Tiers.
    """
    
    MAX_GAP_LOOPS = 2
    MIN_CLAIMS = 15
    MIN_C_CLAIMS = 5
    
    def __init__(self, tiers: Dict[str, str] = None):
        self.tiers = tiers or {}
        self.logger: Optional[SessionLogger] = None
        self.mcp = get_mcp_server()
        
        # State
        self.claim_register: Optional[ClaimRegister] = None
        self.evidence_packs: Dict[str, EvidencePack] = {}
        self.article: str = ""
        self.source_index: Dict[str, int] = {}  # URL -> Nummer für konsistente Referenzierung
    
    def _get_model(self, agent_type: str) -> tuple[str, str]:
        """
        Gibt Modellname und Provider für einen Agent-Typ zurück.
        
        Args:
            agent_type: 'orchestrator', 'researcher', 'writer', 'editor', 'verifier'
        
        Returns:
            (model_name, provider)
        """
        tier = self.tiers.get(agent_type, self.tiers.get("writer", "premium"))
        
        # Mapping: Evidence-Gated Agent -> Config Agent Type
        type_mapping = {
            "claim_miner": "orchestrator",  # Kritische Analyse -> Orchestrator-Modell
            "writer": "writer",
            "editor": "editor",
            "verifier": "verifier",
        }
        
        config_type = type_mapping.get(agent_type, agent_type)
        
        try:
            model_config = get_model_for_agent(config_type, tier)
            return model_config.name, model_config.provider
        except KeyError:
            # Fallback
            if tier == "premium":
                return "claude-sonnet-4-5", "anthropic"
            return "gpt-4o", "openai"
    

    def _parse_json_robust(self, text: str, context: str = "") -> dict:
        """
        Robustes JSON-Parsing mit mehreren Fallback-Strategien.
        
        Strategien:
        1. ```json ... ``` Block
        2. ``` ... ``` Block (ohne json Tag)
        3. Erstes { ... } im Text finden
        4. Text bereinigen und erneut versuchen
        """
        import json
        import re
        
        strategies = []
        
        # Strategie 1: ```json ... ``` Block
        match1 = re.search(r'```json\s*([\s\S]*?)```', text)
        if match1:
            strategies.append(("json_block", match1.group(1).strip()))
        
        # Strategie 2: ``` ... ``` Block (ohne json)
        match2 = re.search(r'```\s*([\s\S]*?)```', text)
        if match2:
            strategies.append(("code_block", match2.group(1).strip()))
        
        # Strategie 3: Erstes { ... } finden (greedy für verschachtelte Objekte)
        # Finde die Position des ersten {
        first_brace = text.find('{')
        if first_brace != -1:
            # Zähle Klammern um das Ende zu finden
            depth = 0
            end_pos = first_brace
            for i, char in enumerate(text[first_brace:], start=first_brace):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > first_brace:
                strategies.append(("brace_match", text[first_brace:end_pos]))
        
        # Strategie 4: Ganzer Text (falls es reines JSON ist)
        strategies.append(("raw_text", text.strip()))
        
        # Versuche alle Strategien
        last_error = None
        for strategy_name, json_str in strategies:
            try:
                data = json.loads(json_str)
                # Erfolg! Logge welche Strategie funktioniert hat
                if strategy_name != "json_block":
                    print(f"[{context}] JSON parsed mit Strategie: {strategy_name}")
                return data
            except json.JSONDecodeError as e:
                last_error = e
                continue
        
        # Alle Strategien fehlgeschlagen
        # Logge die ersten 500 Zeichen für Debugging
        preview = text[:500].replace('\n', '\\n')
        print(f"[{context}] JSON-Parsing FEHLGESCHLAGEN!")
        print(f"[{context}] Text-Preview: {preview}...")
        print(f"[{context}] Letzter Fehler: {last_error}")
        
        raise ValueError(f"Konnte JSON nicht parsen: {last_error}")


    def process(
        self,
        question: str
    ) -> Generator[AgentEvent, None, Dict[str, Any]]:
        """
        Führt den kompletten Evidence-Gated Workflow durch.
        """
        # Logger initialisieren
        self.logger = SessionLogger(
            question=question,
            settings={"mode": "evidence_gated", "tiers": self.tiers}
        )
        
        try:
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="🚀 Starte Evidence-Gated Workflow..."
            )
            
            # ===== PHASE 1 & 2: Query Normalization + Claim Mining =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="📋 Phase 1-2/8: Query Normalization & Claim Mining..."
            )
            
            claim_register = yield from self._phase_1_2_claim_mining(question)
            self.claim_register = claim_register
            
            # Validierung
            validation = claim_register.validate()
            
            # === KRITISCHER CHECK: Ohne Claims kein Artikel! ===
            if validation['stats']['total_claims'] == 0:
                error_msg = "❌ KRITISCHER FEHLER: ClaimMiner hat 0 Claims generiert. " \
                           "Ohne Claims kann kein wissenschaftlicher Artikel erstellt werden. " \
                           "Bitte erneut versuchen."
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name="Orchestrator",
                    content=error_msg
                )
                # Prozess abbrechen
                self.logger.abort(reason=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "article_path": None
                }
            
            if not validation["valid"]:
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name="Orchestrator",
                    content=f"⚠️ ClaimRegister: {'; '.join(validation['issues'])}"
                )
                # Bei zu wenigen Claims trotzdem abbrechen
                if validation['stats']['total_claims'] < 5:
                    error_msg = f"❌ Zu wenige Claims ({validation['stats']['total_claims']}). " \
                               f"Mindestens 5 Claims erforderlich für einen Artikel."
                    yield AgentEvent(
                        event_type=EventType.ERROR,
                        agent_name="Orchestrator",
                        content=error_msg
                    )
                    self.logger.abort(reason=error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "article_path": None
                    }
            else:
                yield AgentEvent(
                    event_type=EventType.STATUS,
                    agent_name="Orchestrator",
                    content=f"✅ {validation['stats']['total_claims']} Claims "
                            f"(A:{validation['stats']['a_claims']}, B:{validation['stats']['b_claims']}, "
                            f"C:{validation['stats']['c_claims']})"
                )
            
            # ===== PHASE 3-4: Evidence Planning & Retrieval =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="🔍 Phase 3-4/8: Targeted Retrieval..."
            )
            
            yield from self._phase_3_4_retrieval()
            
            # === CHECK: Wurden genug Quellen gefunden? ===
            total_sources = sum(len(ep.sources) for ep in self.evidence_packs.values())
            if total_sources == 0:
                error_msg = "❌ KRITISCHER FEHLER: Keine Quellen gefunden. " \
                           "Ohne Quellen kann kein wissenschaftlicher Artikel erstellt werden. " \
                           "Bitte erneut versuchen oder Thema anpassen."
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name="Orchestrator",
                    content=error_msg
                )
                self.logger.abort(reason=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "article_path": None
                }
            elif total_sources < 5:
                yield AgentEvent(
                    event_type=EventType.STATUS,
                    agent_name="Orchestrator",
                    content=f"⚠️ Nur {total_sources} Quellen gefunden - Artikel könnte dünn werden"
                )
            
            # ===== PHASE 5: Evidence Rating =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="⚖️ Phase 5/8: Evidence Rating..."
            )
            
            yield from self._phase_5_rating()
            
            # ===== Quellen-Index aufbauen für konsistente Referenzierung =====
            self._build_source_index()
            
            # ===== PHASE 6: Claim-Bounded Writing =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="✍️ Phase 6/8: Claim-Bounded Writing..."
            )
            
            self.article = yield from self._phase_6_writing()
            
            # ===== PHASE 7: Editorial Review mit Loop =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="📋 Phase 7/8: Editorial Review..."
            )
            
            # Review-Loop (max. 2 Revisionen)
            max_revisions = 2
            for revision_round in range(max_revisions + 1):
                verdict = yield from self._phase_7_editorial_review(revision_round)
                
                if verdict.verdict == "approved":
                    yield AgentEvent(
                        event_type=EventType.STATUS,
                        agent_name="Editor",
                        content=f"✅ Artikel genehmigt (Konfidenz: {verdict.confidence:.0%})"
                    )
                    break
                    
                elif verdict.verdict == "research" and verdict.has_content_gaps():
                    # Nachrecherche für Lücken
                    if revision_round < max_revisions:
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name="Editor",
                            content=f"🔍 Nachrecherche erforderlich..."
                        )
                        yield from self._handle_research_gaps(verdict)
                        # Danach Revision
                        self.article = yield from self._revise_article(verdict)
                    
                elif verdict.verdict == "revise":
                    if revision_round < max_revisions:
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name="Editor",
                            content=f"✏️ Revision {revision_round + 1}/{max_revisions}..."
                        )
                        self.article = yield from self._revise_article(verdict)
                    else:
                        yield AgentEvent(
                            event_type=EventType.STATUS,
                            agent_name="Editor",
                            content=f"⚠️ Max. Revisionen erreicht, fahre fort..."
                        )
                else:
                    # Unbekanntes Verdict, weitermachen
                    break
            
            # ===== PHASE 8: Final Verification =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="📚 Phase 8/8: Bibliography & Polish..."
            )
            
            self.article = self._add_bibliography()
            
            # ===== POST-PROCESSING: Prozess-Artefakte entfernen =====
            self.article = self._polish_article(self.article)
            
            # ===== SPEICHERN =====
            article_path = self._save_article(question)
            
            self.logger.complete(
                article_path=article_path,
                article_words=len(self.article.split())
            )
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content=f"💾 Artikel gespeichert: {os.path.basename(article_path)}"
            )
            
            yield AgentEvent(
                event_type=EventType.RESPONSE,
                agent_name="Orchestrator",
                content="✅ Evidence-Gated Workflow abgeschlossen!",
                data={
                    "article_path": article_path,
                    "mode": "evidence_gated",
                    "claims_total": len(self.claim_register.claims),
                    "sources_total": sum(len(p.sources) for p in self.evidence_packs.values()),
                    "article_length": len(self.article),
                    "log_file": self.logger.get_log_filename()
                }
            )
            
            return {
                "success": True,
                "article_path": article_path,
                "log_file": self.logger.get_log_filename()
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(str(e))
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name="Orchestrator",
                content=f"❌ Fehler: {e}"
            )
            raise
    
    def _phase_1_2_claim_mining(self, question: str) -> Generator[AgentEvent, None, ClaimRegister]:
        """Phase 1-2: Erstellt ClaimRegister mit dynamischer Modellauswahl."""
        
        # Dynamische Modellauswahl
        model_name, provider = self._get_model("claim_miner")
        tier = self.tiers.get("orchestrator", "premium")
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="ClaimMiner",
            content=f"⛏️ Mining Claims mit {model_name}..."
        )
        
        prompt = f"""Du bist ein Claim Mining Agent für wissenschaftliche Artikel.

FRAGE: {question}

AUFGABE: Erstelle ein ClaimRegister mit:
1. QuestionBrief (präzisierte Frage)
2. TermMap (Synonyme, Suchvarianten, Negative Keywords)
3. Outline (Gliederung für 12-15 Seiten)
4. Claims (MINDESTENS 20 Claims, davon MINDESTENS 7 C-Claims!)

CLAIM-TYPEN:
- definition: "X ist ..."
- mechanism: "X funktioniert so, dass ..."
- comparison: "X unterscheidet sich von Y durch ..."
- effect: "X führt zu ..."
- quant: Zahlen, Prozente
- temporal: Zeitangaben, Releases
- normative: Empfehlungen

EVIDENZKLASSEN:
- A: Stabiles Wissen, keine Quelle nötig
- B: 1 gute Quelle
- C: 2+ unabhängige Quellen (für Zahlen, aktuelle Fakten!)

WICHTIGE STRUKTUR-ANFORDERUNGEN:
- Sektion 1 MUSS "Executive Summary / Management Summary" sein (2-3 Claims)
- Jede weitere Sektion sollte 2-4 Claims haben
- MINDESTENS 8 Sektionen für einen 12-15 Seiten Artikel
- Jeder B/C-Claim braucht ein retrieval_ticket mit 2-3 Queries!

OUTPUT: NUR JSON, kein anderer Text!

```json
{{
  "question_brief": {{
    "core_question": "...",
    "audience": "Fachexperten",
    "tone": "wissenschaftlich",
    "target_pages": 12,
    "as_of_date": "{date.today().isoformat()}",
    "freshness_priority": "high",
    "scope_in": ["..."],
    "scope_out": ["..."]
  }},
  "term_map": {{
    "canonical_terms": ["Begriff1", "Begriff2"],
    "synonyms": {{"Begriff1": ["Syn1", "Syn2"]}},
    "negative_keywords": ["Falsche Treffer"],
    "disambiguation_notes": ["Klärungen"],
    "search_variants": {{"Begriff1": ["Variante1", "Variante2"]}}
  }},
  "outline": {{
    "sections": [
      {{"number": "1", "title": "Executive Summary", "goal": "Kernaussagen kompakt", "expected_claim_ids": ["C-01", "C-02"], "estimated_pages": 1.0}},
      {{"number": "2", "title": "...", "goal": "...", "expected_claim_ids": ["C-03", "C-04", "C-05"], "estimated_pages": 1.5}}
    ]
  }},
  "claims": [
    {{
      "claim_id": "C-01",
      "claim_text": "...",
      "claim_type": "definition",
      "evidence_class": "A",
      "section_id": "1",
      "retrieval_ticket": null
    }},
    {{
      "claim_id": "C-02",
      "claim_text": "...",
      "claim_type": "temporal",
      "evidence_class": "C",
      "freshness_required": true,
      "section_id": "2",
      "retrieval_ticket": {{
        "queries": ["Query 1", "Query 2", "Query 3"],
        "min_sources": 2
      }}
    }}
  ]
}}
```"""

        # === LOGGING: Start ClaimMiner Step ===
        step_idx = self.logger.start_step(
            agent="ClaimMiner",
            model=model_name,
            provider=provider,
            tier=tier,
            action="claim_mining",
            task=f"Erstelle ClaimRegister für: {question[:80]}..."
        )
        
        try:
            # Provider-spezifischer API-Aufruf
            if provider == "anthropic":
                from anthropic import Anthropic
                from config import ANTHROPIC_API_KEY
                
                client = Anthropic(api_key=ANTHROPIC_API_KEY)
                response = client.messages.create(
                    model=model_name,
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
                tokens = {
                    "input": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.output_tokens if hasattr(response, 'usage') else 0
                }
            else:
                from openai import OpenAI
                from config import OPENAI_API_KEY
                
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=8000
                )
                result_text = response.choices[0].message.content
                tokens = {
                    "input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.completion_tokens if hasattr(response, 'usage') else 0
                }
            
            # JSON parsen - ROBUST mit mehreren Strategien
            data = self._parse_json_robust(result_text, "ClaimMiner")
            
            # QuestionBrief
            qb_data = data.get("question_brief", {})
            question_brief = QuestionBrief(
                core_question=qb_data.get("core_question", question),
                original_question=question,
                audience=qb_data.get("audience", "Fachexperten"),
                tone=qb_data.get("tone", "wissenschaftlich"),
                target_pages=qb_data.get("target_pages", 12),
                as_of_date=qb_data.get("as_of_date", date.today().isoformat()),
                freshness_priority=qb_data.get("freshness_priority", "high"),
                scope_in=qb_data.get("scope_in", []),
                scope_out=qb_data.get("scope_out", [])
            )
            
            # TermMap
            tm_data = data.get("term_map", {})
            term_map = TermMap(
                canonical_terms=tm_data.get("canonical_terms", []),
                synonyms=tm_data.get("synonyms", {}),
                negative_keywords=tm_data.get("negative_keywords", []),
                disambiguation_notes=tm_data.get("disambiguation_notes", []),
                search_variants=tm_data.get("search_variants", {})
            )
            
            # Outline
            outline_data = data.get("outline", {})
            sections = []
            for s in outline_data.get("sections", []):
                sections.append(OutlineSection(
                    number=s.get("number", ""),
                    title=s.get("title", ""),
                    goal=s.get("goal", ""),
                    expected_claim_ids=s.get("expected_claim_ids", []),
                    estimated_pages=s.get("estimated_pages", 1.0)
                ))
            outline = Outline(sections=sections)
            
            # Claims
            claims = []
            for c in data.get("claims", []):
                ticket_data = c.get("retrieval_ticket")
                ticket = None
                if ticket_data:
                    ticket = RetrievalTicket(
                        queries=ticket_data.get("queries", []),
                        min_sources=ticket_data.get("min_sources", 1),
                        preferred_domains=ticket_data.get("preferred_domains", []),
                        excluded_domains=ticket_data.get("excluded_domains", [])
                    )
                
                claims.append(Claim(
                    claim_id=c.get("claim_id", f"C-{len(claims)+1:02d}"),
                    claim_text=c.get("claim_text", ""),
                    claim_type=ClaimType(c.get("claim_type", "definition")),
                    evidence_class=EvidenceClass(c.get("evidence_class", "B")),
                    freshness_required=c.get("freshness_required", False),
                    section_id=c.get("section_id", ""),
                    retrieval_ticket=ticket
                ))
            
            # === LOGGING: End ClaimMiner Step (Success) ===
            self.logger.end_step(
                step_idx,
                status="success",
                tokens=tokens,
                result_length=len(result_text),
                details={
                    "claims_count": len(claims),
                    "a_claims": sum(1 for c in claims if c.evidence_class == EvidenceClass.A),
                    "b_claims": sum(1 for c in claims if c.evidence_class == EvidenceClass.B),
                    "c_claims": sum(1 for c in claims if c.evidence_class == EvidenceClass.C),
                    "sections_count": len(sections),
                    "model_used": model_name
                }
            )
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="ClaimMiner",
                content=f"✅ {len(claims)} Claims in {len(sections)} Sektionen extrahiert"
            )
            
            return ClaimRegister(
                question_brief=question_brief,
                term_map=term_map,
                outline=outline,
                claims=claims,
                min_total_claims=self.MIN_CLAIMS,
                min_c_claims=self.MIN_C_CLAIMS
            )
            
        except Exception as e:
            # === LOGGING: End ClaimMiner Step (Error) ===
            self.logger.end_step(
                step_idx,
                status="error",
                error=str(e)
            )
            
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name="ClaimMiner",
                content=f"❌ Fehler: {e}"
            )
            # Fallback
            return ClaimRegister(
                question_brief=QuestionBrief(
                    core_question=question,
                    original_question=question,
                    audience="Fachexperten",
                    tone="wissenschaftlich"
                ),
                term_map=TermMap(
                    canonical_terms=[],
                    synonyms={},
                    negative_keywords=[],
                    disambiguation_notes=[],
                    search_variants={}
                ),
                outline=Outline(sections=[]),
                claims=[]
            )
    
    def _phase_3_4_retrieval(self) -> Generator[AgentEvent, None, None]:
        """Phase 3-4: Recherche für B/C Claims."""
        claims_needing_evidence = self.claim_register.get_claims_needing_evidence()
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Retriever",
            content=f"🔍 Recherche für {len(claims_needing_evidence)} Claims..."
        )
        
        # === LOGGING: Start Retrieval Step ===
        step_idx = self.logger.start_step(
            agent="TargetedRetriever",
            model="tool-based",
            provider="mcp",
            tier="standard",
            action="targeted_retrieval",
            task=f"Recherche für {len(claims_needing_evidence)} Claims"
        )
        
        total_sources = 0
        tools_used = []
        
        for claim in claims_needing_evidence:
            if not claim.retrieval_ticket or not claim.retrieval_ticket.queries:
                continue
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Retriever",
                content=f"   {claim.claim_id}: {claim.claim_text[:50]}..."
            )
            
            # Tool auswählen
            tool = self._select_tool(claim)
            if tool not in tools_used:
                tools_used.append(tool)
            
            sources = []
            
            for query in claim.retrieval_ticket.queries[:3]:
                try:
                    result = self.mcp.call_tool(f"{tool}_search", {"query": query, "max_results": 3})
                    
                    if result and result.get("results"):
                        for item in result["results"]:
                            source = Source(
                                source_id=f"S-{claim.claim_id}-{len(sources)+1:02d}",
                                title=item.get("title", ""),
                                publisher=self._extract_publisher(item.get("url", "")),
                                url=item.get("url", ""),
                                extract=item.get("snippet", "")[:400],
                                supports_claims=[claim.claim_id]
                            )
                            sources.append(source)
                            
                            if len(sources) >= claim.min_sources + 2:
                                break
                except Exception as e:
                    pass
                
                if len(sources) >= claim.min_sources:
                    break
            
            status = ClaimStatus.FULFILLED if len(sources) >= claim.min_sources else ClaimStatus.INSUFFICIENT
            
            self.evidence_packs[claim.claim_id] = EvidencePack(
                claim_id=claim.claim_id,
                sources=sources,
                status=status
            )
            
            total_sources += len(sources)
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Retriever",
                content=f"   {'✅' if status == ClaimStatus.FULFILLED else '⚠️'} {len(sources)} Quellen"
            )
        
        # === LOGGING: End Retrieval Step ===
        fulfilled = sum(1 for p in self.evidence_packs.values() if p.status == ClaimStatus.FULFILLED)
        self.logger.end_step(
            step_idx,
            status="success",
            result_length=total_sources,
            tool_calls=tools_used,
            details={
                "claims_processed": len(claims_needing_evidence),
                "claims_fulfilled": fulfilled,
                "total_sources": total_sources,
                "tools_used": tools_used
            }
        )
    
    def _phase_5_rating(self) -> Generator[AgentEvent, None, None]:
        """Phase 5: Quellen bewerten."""
        
        # === LOGGING: Start Rating Step ===
        step_idx = self.logger.start_step(
            agent="EvidenceRater",
            model="rule-based",
            provider="internal",
            tier="standard",
            action="evidence_rating",
            task="Bewerte Quellen nach Autorität und Unabhängigkeit"
        )
        
        rated_count = 0
        for claim_id, pack in self.evidence_packs.items():
            for source in pack.sources:
                # Einfache automatische Bewertung
                is_vendor = any(vendor in source.url.lower() for vendor in ["servicenow.com", "microsoft.com", "google.com", "aws.amazon.com"])
                source.rating = SourceRating(
                    authority=2 if is_vendor else 1,
                    independence=1 if is_vendor else 2,
                    recency=2,
                    specificity=2,
                    consensus=1
                )
                rated_count += 1
        
        # === LOGGING: End Rating Step ===
        self.logger.end_step(
            step_idx,
            status="success",
            result_length=rated_count,
            details={"sources_rated": rated_count}
        )
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Rater",
            content=f"✅ {rated_count} Quellen bewertet"
        )
    
    def _build_source_index(self):
        """
        Baut einen konsistenten Quellen-Index auf.
        Jede URL bekommt eine eindeutige Nummer für die Referenzierung.
        """
        self.source_index = {}
        counter = 1
        
        for pack in self.evidence_packs.values():
            for source in pack.sources:
                if source.url not in self.source_index:
                    self.source_index[source.url] = counter
                    counter += 1
    
    def _get_sources_for_claim(self, claim_id: str) -> List[Dict[str, Any]]:
        """
        Gibt alle Quellen für einen Claim mit ihren Index-Nummern zurück.
        """
        pack = self.evidence_packs.get(claim_id)
        if not pack:
            return []
        
        sources = []
        for source in pack.sources:
            idx = self.source_index.get(source.url, 0)
            sources.append({
                "index": idx,
                "title": source.title,
                "publisher": source.publisher,
                "url": source.url,
                "extract": source.extract[:200]
            })
        return sources
    
    def _phase_6_writing(self) -> Generator[AgentEvent, None, str]:
        """Phase 6: Artikel schreiben mit korrekten Quellenverweisen."""
        
        # Dynamische Modellauswahl
        model_name, provider = self._get_model("writer")
        tier = self.tiers.get("writer", "premium")
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Writer",
            content=f"✍️ Schreibe Artikel mit {model_name}..."
        )
        
        # Claims mit echten Quellen aufbereiten
        claims_with_sources = []
        for claim in self.claim_register.claims:
            claim_data = {
                "id": claim.claim_id,
                "text": claim.claim_text,
                "type": claim.claim_type.value,
                "section": claim.section_id,
                "sources": []
            }
            
            if claim.evidence_class == EvidenceClass.A:
                claim_data["evidence"] = "A (keine Quelle nötig)"
            else:
                sources = self._get_sources_for_claim(claim.claim_id)
                if sources:
                    claim_data["evidence"] = f"{claim.evidence_class.value} (belegt)"
                    claim_data["sources"] = sources
                else:
                    claim_data["evidence"] = f"{claim.evidence_class.value} (NICHT BELEGT - vorsichtig formulieren!)"
            
            claims_with_sources.append(claim_data)
        
        # Claims als formatierter Text
        claims_text = ""
        for c in claims_with_sources:
            claims_text += f"\n### {c['id']} (Sektion {c['section']}, {c['evidence']})\n"
            claims_text += f"Aussage: {c['text']}\n"
            if c['sources']:
                claims_text += "Quellen:\n"
                for s in c['sources']:
                    claims_text += f"  - [{s['index']}] {s['publisher']}: {s['title']}\n"
                    claims_text += f"    URL: {s['url']}\n"
                    claims_text += f"    Auszug: {s['extract']}...\n"
        
        # Outline
        outline_text = ""
        for s in self.claim_register.outline.sections:
            outline_text += f"\n{s.number}. {s.title}\n"
            outline_text += f"   Ziel: {s.goal}\n"
            outline_text += f"   Claims: {', '.join(s.expected_claim_ids)}\n"
            outline_text += f"   Umfang: ca. {s.estimated_pages} Seiten\n"
        
        prompt = f"""Du bist ein wissenschaftlicher Autor und schreibst einen Expertenartikel.

# KERNFRAGE
{self.claim_register.question_brief.core_question}

# ARTIKEL-STRUKTUR (UNBEDINGT EINHALTEN!)
{outline_text}

# VERWENDBARE CLAIMS MIT QUELLEN
{claims_text}

# STRIKTE SCHREIBREGELN

## 1. Quellenverweise
- Verwende NUR die Quellennummern [1], [2], [3] etc. wie oben angegeben
- Setze Quellenverweise DIREKT nach der Aussage: "ServiceNow ist eine Cloud-Plattform [1]."
- Bei mehreren Quellen: "Dies wird von mehreren Studien bestätigt [2][3][5]."
- KEINE Claim-Anchors im Text! Die (C-01) etc. sind nur für dich zur Orientierung.

## 2. Artikellänge (KRITISCH!)
- MINDESTENS 3000 Wörter (ca. 12-15 Seiten)
- Executive Summary: 300-400 Wörter
- Jedes Hauptkapitel: MINDESTENS 400-600 Wörter
- Ausführliche Erklärungen, Beispiele, Kontext!

## 3. Struktur
- Beginne mit "# [Titel]"
- Dann "## Executive Summary" (PFLICHT!)
- Dann die weiteren Kapitel gemäß Outline
- Jedes Kapitel mit "## [Nummer]. [Titel]"
- Unterkapitel mit "### [Titel]" wenn sinnvoll

## 4. Stil
- Wissenschaftlich, aber verständlich
- Konkrete Beispiele und Anwendungsfälle
- Kritische Einordnung wo angebracht
- Am Ende: "## Limitations" Abschnitt

## 5. VERBOTEN
- Keine erfundenen Fakten ohne Quelle
- Keine Claim-Anchors (C-01) im finalen Text
- Kein "laut Quelle X" - nutze [X] Notation
- Keine Aufzählungen als Hauptinhalt - ausführliche Fließtexte!

SCHREIBE JETZT DEN VOLLSTÄNDIGEN ARTIKEL (mindestens 3000 Wörter):"""

        # === LOGGING: Start Writer Step ===
        step_idx = self.logger.start_step(
            agent="ClaimBoundedWriter",
            model=model_name,
            provider=provider,
            tier=tier,
            action="article_writing",
            task=f"Schreibe Artikel mit {len(claims_with_sources)} Claims"
        )
        
        try:
            # Provider-spezifischer API-Aufruf
            if provider == "openai":
                from openai import OpenAI
                from config import OPENAI_API_KEY
                
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=16000  # Mehr Tokens für längeren Artikel
                )
                article = response.choices[0].message.content
                tokens = {
                    "input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.completion_tokens if hasattr(response, 'usage') else 0
                }
            else:
                from anthropic import Anthropic
                from config import ANTHROPIC_API_KEY
                
                client = Anthropic(api_key=ANTHROPIC_API_KEY)
                response = client.messages.create(
                    model=model_name,
                    max_tokens=16000,  # Erhöht für längere Artikel
                    messages=[{"role": "user", "content": prompt}]
                )
                article = response.content[0].text
                tokens = {
                    "input": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.output_tokens if hasattr(response, 'usage') else 0
                }
            
            word_count = len(article.split())
            
            # === LOGGING: End Writer Step (Success) ===
            self.logger.end_step(
                step_idx,
                status="success",
                tokens=tokens,
                result_length=len(article),
                details={
                    "claims_provided": len(claims_with_sources),
                    "article_chars": len(article),
                    "article_words": word_count,
                    "model_used": model_name
                }
            )
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Writer",
                content=f"✅ Artikel: {word_count} Wörter, {len(article)} Zeichen"
            )
            
            return article
            
        except Exception as e:
            # === LOGGING: End Writer Step (Error) ===
            self.logger.end_step(
                step_idx,
                status="error",
                error=str(e)
            )
            raise
    
    def _add_bibliography(self) -> str:
        """Fügt Literaturverzeichnis mit konsistenter Nummerierung hinzu.
        
        Nur Quellen die tatsächlich im Artikel referenziert werden ([1], [2], etc.)
        werden ins Verzeichnis aufgenommen.
        """
        
        # === LOGGING: Start Bibliography Step ===
        step_idx = self.logger.start_step(
            agent="BibliographyBuilder",
            model="rule-based",
            provider="internal",
            tier="standard",
            action="build_bibliography",
            task="Erstelle Literaturverzeichnis"
        )
        
        if not self.source_index:
            self.logger.end_step(step_idx, status="success", result_length=0)
            return self.article
        
        # Finde alle im Artikel verwendeten Quellennummern [1], [2], etc.
        used_refs = set(int(m) for m in re.findall(r'\[(\d+)\]', self.article))
        
        # Sortiere nach Index
        sorted_sources = sorted(self.source_index.items(), key=lambda x: x[1])
        
        # Sammle Source-Details
        url_to_source = {}
        for pack in self.evidence_packs.values():
            for source in pack.sources:
                if source.url not in url_to_source:
                    url_to_source[source.url] = source
        
        bib = "\n\n---\n\n## Literaturverzeichnis\n\n"
        included_count = 0
        for url, idx in sorted_sources:
            # Nur Quellen aufnehmen die im Text referenziert werden
            if idx not in used_refs:
                continue
            
            source = url_to_source.get(url)
            if source:
                bib += f"[{idx}] {source.publisher}: {source.title}. {url}\n\n"
            else:
                bib += f"[{idx}] {url}\n\n"
            included_count += 1
        
        # === LOGGING: End Bibliography Step ===
        self.logger.end_step(
            step_idx,
            status="success",
            result_length=included_count,
            details={
                "unique_sources": len(sorted_sources),
                "sources_in_article": included_count,
                "filtered_out": len(sorted_sources) - included_count
            }
        )
        
        return self.article + bib
    
    def _select_tool(self, claim: Claim) -> str:
        """Wählt Tool für Claim."""
        text = claim.claim_text.lower()
        
        if any(kw in text for kw in ["studie", "forschung", "prozent", "wissenschaft"]):
            return "semantic_scholar"
        if any(kw in text for kw in ["release", "version", "2024", "2025", "2026", "aktuell"]):
            return "gnews"
        if any(kw in text for kw in ["erfahrung", "vergleich", "community", "entwickler"]):
            return "hackernews"
        
        return "tavily"
    
    def _extract_publisher(self, url: str) -> str:
        """Extrahiert Publisher aus URL."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            return domain.split(".")[0].title()
        except:
            return "Unbekannt"
    
    def _polish_article(self, article: str) -> str:
        """
        Post-Processing: Entfernt Prozess-Artefakte aus dem finalen Artikel.
        
        Entfernt:
        - Meta-Kommentare über Überarbeitungen
        - Hinweise auf "ursprüngliche Fassung"
        - Klammerzusätze wie "(Abschnitt vervollständigt)"
        - Editor/Writer Prozessinformationen
        """
        if not article:
            return article
        
        # Patterns für Prozess-Artefakte
        patterns_to_remove = [
            # Überschriften-Zusätze in Klammern
            r'\s*\(Abschnitt\s+(?:vervollständigt|ergänzt|überarbeitet|neu)\)',
            r'\s*\((?:neu|ergänzt|überarbeitet|erweitert)(?:;[^)]+)?\)',
            r'\s*\(zuvor\s+(?:fehlend|unvollständig|abstrakt)\)',
            r'\s*\(praxisorientiert\s+ergänzt[^)]*\)',
            r'\s*\(Hamburg[‑-]Bezug\s+geschärft\)',
            
            # Meta-Sätze über Überarbeitungen (am Satzanfang)
            r'(?:^|\n)Die\s+ursprüngliche\s+(?:Fassung|Version)\s+[^.]+\.\s*',
            r'(?:^|\n)Der\s+ursprüngliche\s+Text\s+[^.]+\.\s*',
            r'(?:^|\n)In\s+der\s+(?:ursprünglichen|vorherigen)\s+(?:Fassung|Version)\s+[^.]+\.\s*',
            r'(?:^|\n)Dieser\s+Abschnitt\s+wurde\s+(?:überarbeitet|ergänzt|erweitert)[^.]*\.\s*',
            r'(?:^|\n)Die\s+vorliegende\s+Überarbeitung\s+[^.]+\.\s*',
            
            # Fettgedruckte Meta-Hinweise
            r'\*\*Ergänzend[^*]+\*\*',
            r'\*\*(?:Zur\s+)?(?:Behebung|Schließung)\s+der\s+(?:zuvor\s+)?kritisierten\s+(?:Lücke|Lücken)[^*]*\*\*',
            r'\*\*(?:Neu|Ergänzt|Korrigiert)[^*]*\*\*:?\s*',
            
            # Hinweise in Klammern im Fließtext
            r'\s*\((?:siehe|vgl\.?)\s+(?:ursprüngliche|vorherige)\s+(?:Fassung|Version)\)',
            r'\s*\((?:diese|jene)\s+Lücke\s+wurde\s+(?:geschlossen|behoben)\)',
        ]
        
        cleaned = article
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        # Aufräumen: Mehrfache Leerzeilen reduzieren
        cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)
        
        # Aufräumen: Leerzeichen vor Satzzeichen
        cleaned = re.sub(r'\s+([.,;:!?])', r'\1', cleaned)
        
        # Aufräumen: Mehrfache Leerzeichen
        cleaned = re.sub(r'  +', ' ', cleaned)
        
        return cleaned.strip()
    
    def _save_article(self, question: str) -> str:
        """Speichert Artikel."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in question[:50])
        safe_name = safe_name.strip().replace(" ", "_").lower()
        
        timestamp = self.logger.session_id if self.logger else datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.article)
        
        return filepath
    
    # =========================================================================
    # PHASE 7: Editorial Review
    # =========================================================================
    
    def _phase_7_editorial_review(self, revision_round: int) -> Generator[AgentEvent, None, Any]:
        """
        Phase 7: Editor prüft den Artikel und gibt strukturiertes Feedback.
        
        Returns:
            EditorVerdict mit verdict (approved/revise/research)
        """
        from agents.editor import EditorVerdict
        
        # Dynamische Modellauswahl
        model_name, provider = self._get_model("editor")
        tier = self.tiers.get("editor", "premium")
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Editor",
            content=f"🔍 Prüfe Artikel mit {model_name}..."
        )
        
        # Statistiken für den Editor
        word_count = len(self.article.split())
        source_refs = len(re.findall(r'\[\d+\]', self.article))
        has_exec_summary = "Executive Summary" in self.article or "Management Summary" in self.article
        has_limitations = "Limitation" in self.article
        
        prompt = f"""Du bist ein kritischer Editor für wissenschaftliche Fachartikel.

# ARTIKEL ZU PRÜFEN
{self.article[:15000]}  # Erste 15000 Zeichen

# ARTIKEL-STATISTIKEN
- Wörter: {word_count}
- Quellenverweise im Text: {source_refs}
- Executive Summary vorhanden: {has_exec_summary}
- Limitations-Abschnitt vorhanden: {has_limitations}

# PRÜFKRITERIEN

## 1. Länge (KRITISCH!)
- MINDESTENS 2500 Wörter für einen vollständigen Artikel
- Aktuell: {word_count} Wörter
- Bei < 2500: verdict = "revise"

## 2. Quellenreferenzierung
- Sind Quellen [1], [2], etc. im Text referenziert?
- Werden verschiedene Quellen genutzt (nicht nur [1]-[3])?
- Aktuell: {source_refs} Quellenverweise

## 3. Struktur
- Hat der Artikel eine Executive Summary?
- Sind alle Kapitel ausreichend ausgeführt (nicht nur 2-3 Sätze)?
- Gibt es einen Limitations-Abschnitt?

## 4. Inhaltliche Qualität
- Werden die Kernfragen beantwortet?
- Sind die Informationen konsistent?
- Gibt es Lücken oder fehlende wichtige Aspekte?

# OUTPUT-FORMAT (JSON!)

Antworte NUR mit diesem JSON (keine weitere Erklärung):

```json
{{
  "verdict": "approved|revise|research",
  "confidence": 0.0-1.0,
  "summary": "Kurze Zusammenfassung der Bewertung",
  "issues": [
    {{
      "type": "length|sources|structure|content_gap",
      "description": "Was ist das Problem?",
      "severity": "critical|major|minor",
      "suggested_action": "revise|research",
      "research_query": "Falls research nötig: Suchquery"
    }}
  ]
}}
```

WICHTIG: 
- "approved" NUR wenn Artikel > 2500 Wörter UND gute Quellenreferenzierung UND vollständige Struktur
- "revise" bei Strukturproblemen, zu kurz, oder stilistischen Issues
- "research" NUR wenn konkrete Fakten/Daten fehlen die recherchiert werden müssen

DEIN VERDICT:"""

        # === LOGGING: Start Editor Step ===
        step_idx = self.logger.start_step(
            agent="EditorialReviewer",
            model=model_name,
            provider=provider,
            tier=tier,
            action="editorial_review",
            task=f"Prüfe Artikel (Revision {revision_round})"
        )
        
        try:
            # Provider-spezifischer API-Aufruf
            if provider == "anthropic":
                from anthropic import Anthropic
                from config import ANTHROPIC_API_KEY
                
                client = Anthropic(api_key=ANTHROPIC_API_KEY)
                response = client.messages.create(
                    model=model_name,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
                tokens = {
                    "input": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.output_tokens if hasattr(response, 'usage') else 0
                }
            else:
                from openai import OpenAI
                from config import OPENAI_API_KEY
                
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=2000
                )
                result_text = response.choices[0].message.content
                tokens = {
                    "input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.completion_tokens if hasattr(response, 'usage') else 0
                }
            
            # Verdict parsen
            verdict = EditorVerdict.from_response(result_text)
            
            # === LOGGING: End Editor Step ===
            self.logger.end_step(
                step_idx,
                status="success",
                tokens=tokens,
                result_length=len(result_text),
                details={
                    "verdict": verdict.verdict,
                    "confidence": verdict.confidence,
                    "issues_count": len(verdict.issues),
                    "word_count_checked": word_count,
                    "model_used": model_name
                }
            )
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Editor",
                content=f"📋 Verdict: {verdict.verdict.upper()} ({len(verdict.issues)} Issues)"
            )
            
            return verdict
            
        except Exception as e:
            self.logger.end_step(step_idx, status="error", error=str(e))
            # Fallback: approved um weiterzumachen
            return EditorVerdict(verdict="approved", confidence=0.3, summary=f"Fehler: {e}")
    
    def _handle_research_gaps(self, verdict) -> Generator[AgentEvent, None, None]:
        """
        Führt Nachrecherche für identifizierte Lücken durch.
        """
        research_queries = verdict.get_research_queries()
        
        if not research_queries:
            return
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Retriever",
            content=f"🔍 Nachrecherche für {len(research_queries)} Lücken..."
        )
        
        # === LOGGING: Start Gap Research Step ===
        step_idx = self.logger.start_step(
            agent="GapRetriever",
            model="tool-based",
            provider="mcp",
            tier="standard",
            action="gap_research",
            task=f"Nachrecherche für {len(research_queries)} Lücken"
        )
        
        new_sources = 0
        for query in research_queries[:5]:  # Max 5 Nachrecherchen
            try:
                result = self.mcp.call_tool("tavily_search", {"query": query, "max_results": 3})
                
                if result and result.get("results"):
                    for item in result["results"]:
                        url = item.get("url", "")
                        if url and url not in self.source_index:
                            # Neue Quelle hinzufügen
                            new_idx = max(self.source_index.values(), default=0) + 1
                            self.source_index[url] = new_idx
                            
                            source = Source(
                                source_id=f"S-GAP-{new_idx:02d}",
                                title=item.get("title", ""),
                                publisher=self._extract_publisher(url),
                                url=url,
                                extract=item.get("snippet", "")[:400],
                                supports_claims=["GAP"]
                            )
                            
                            # Zu einem neuen EvidencePack hinzufügen
                            if "GAP" not in self.evidence_packs:
                                self.evidence_packs["GAP"] = EvidencePack(
                                    claim_id="GAP",
                                    sources=[],
                                    status=ClaimStatus.FULFILLED
                                )
                            self.evidence_packs["GAP"].sources.append(source)
                            new_sources += 1
                            
            except Exception as e:
                pass
        
        # === LOGGING: End Gap Research Step ===
        self.logger.end_step(
            step_idx,
            status="success",
            result_length=new_sources,
            details={
                "queries_processed": len(research_queries),
                "new_sources_found": new_sources
            }
        )
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Retriever",
            content=f"✅ {new_sources} neue Quellen gefunden"
        )
    
    def _revise_article(self, verdict) -> Generator[AgentEvent, None, str]:
        """
        Writer überarbeitet den Artikel basierend auf Editor-Feedback.
        """
        # Dynamische Modellauswahl
        model_name, provider = self._get_model("writer")
        tier = self.tiers.get("writer", "premium")
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Writer",
            content=f"✏️ Überarbeite Artikel mit {model_name}..."
        )
        
        # Feedback aufbereiten
        issues_text = ""
        for issue in verdict.issues:
            issues_text += f"- [{issue.severity.upper()}] {issue.type}: {issue.description}\n"
            issues_text += f"  Aktion: {issue.suggested_action}\n"
        
        # Neue Quellen falls vorhanden
        new_sources_text = ""
        if "GAP" in self.evidence_packs:
            new_sources_text = "\n\n# NEUE QUELLEN (aus Nachrecherche)\n"
            for source in self.evidence_packs["GAP"].sources:
                idx = self.source_index.get(source.url, "?")
                new_sources_text += f"[{idx}] {source.publisher}: {source.title}\n"
                new_sources_text += f"    URL: {source.url}\n"
                new_sources_text += f"    Auszug: {source.extract[:200]}...\n\n"
        
        # Aktuelle Wortanzahl für den Prompt
        current_word_count = len(self.article.split()) if self.article else 0
        
        prompt = f"""Du bist ein erfahrener wissenschaftlicher Lektor. Deine Aufgabe ist eine GEZIELTE ÜBERARBEITUNG.

# EDITOR-FEEDBACK
{verdict.summary}

## Zu behebende Probleme:
{issues_text}
{new_sources_text}

# AKTUELLER ARTIKEL
{self.article}

# ÜBERARBEITUNGSANLEITUNG

## Dein Auftrag
Behebe EXAKT die oben genannten Probleme. Nicht mehr, nicht weniger.

## Issue-spezifische Maßnahmen
- "sources": Füge an den kritisierten Stellen fehlende Quellenverweise [X] ein
- "structure": Ergänze konkret die fehlenden Abschnitte (z.B. Executive Summary, Limitations)
- "content_gap": Vertiefe GENAU die genannten Themen mit den neuen Quellen
- "consistency": Korrigiere PRÄZISE die genannten Widersprüche
- "length": Erweitere die KONKRET kritisierten dünnen Passagen

## Qualitätsprinzipien
1. CHIRURGISCHE PRÄZISION: Ändere nur, was kritisiert wurde
2. KONTEXT BEWAHREN: Bestehende gute Passagen bleiben unverändert
3. QUELLENINTEGRITÄT: Alle [X]-Verweise müssen erhalten bleiben
4. VOLLSTÄNDIGKEIT: Gib den GESAMTEN Artikel zurück (nicht nur Änderungen)

## KRITISCH - KEINE META-KOMMENTARE!
Der finale Artikel ist für LESER bestimmt, NICHT für Editoren. Daher:
- KEINE Hinweise auf "ursprüngliche Fassung" oder "vorherige Version"
- KEINE Kommentare wie "(Abschnitt vervollständigt)", "(neu)", "(ergänzt)"
- KEINE Erklärungen wie "Dieser Abschnitt wurde überarbeitet weil..."
- KEINE Metainformationen über den Überarbeitungsprozess
- Der Leser darf NICHT merken, dass der Text überarbeitet wurde
- Schreibe so, als wäre es die ERSTE und EINZIGE Version

## WICHTIG
- Keine proaktiven "Verbesserungen" an Stellen ohne Kritik
- Kein Fülltext - jede Ergänzung muss einen Issue adressieren
- Der wissenschaftliche Ton bleibt durchgehend sachlich

ÜBERARBEITETER ARTIKEL:"""

        # === LOGGING: Start Revision Step ===
        step_idx = self.logger.start_step(
            agent="ArticleReviser",
            model=model_name,
            provider=provider,
            tier=tier,
            action="article_revision",
            task=f"Überarbeite basierend auf {len(verdict.issues)} Issues"
        )
        
        try:
            # Provider-spezifischer API-Aufruf
            if provider == "openai":
                from openai import OpenAI
                from config import OPENAI_API_KEY
                
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=16000  # Erhöht für längere Revisionen
                )
                revised_article = response.choices[0].message.content
                tokens = {
                    "input": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.completion_tokens if hasattr(response, 'usage') else 0
                }
            else:
                from anthropic import Anthropic
                from config import ANTHROPIC_API_KEY
                
                client = Anthropic(api_key=ANTHROPIC_API_KEY)
                response = client.messages.create(
                    model=model_name,
                    max_tokens=16000,  # Erhöht für längere Revisionen
                    messages=[{"role": "user", "content": prompt}]
                )
                revised_article = response.content[0].text
                tokens = {
                    "input": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                    "output": response.usage.output_tokens if hasattr(response, 'usage') else 0
                }
            
            word_count = len(revised_article.split()) if revised_article else 0
            original_word_count = len(self.article.split()) if self.article else 0
            
            # === FALLBACK: Wenn Revision leer oder viel kürzer, behalte Original ===
            if word_count < 500 or (original_word_count > 0 and word_count < original_word_count * 0.3):
                # Revision ist zu kurz oder leer - behalte das Original!
                self.logger.end_step(
                    step_idx,
                    status="success",  # Technisch erfolgreich, aber Fallback
                    tokens=tokens,
                    result_length=len(self.article),
                    details={
                        "issues_addressed": len(verdict.issues),
                        "new_word_count": original_word_count,
                        "model_used": model_name,
                        "fallback": True,
                        "reason": f"Revision zu kurz ({word_count} Wörter), behalte Original ({original_word_count} Wörter)"
                    }
                )
                
                yield AgentEvent(
                    event_type=EventType.STATUS,
                    agent_name="Writer",
                    content=f"⚠️ Revision fehlgeschlagen ({word_count} Wörter) - behalte Original ({original_word_count} Wörter)"
                )
                
                return self.article  # Behalte das Original!
            
            # === LOGGING: End Revision Step ===
            self.logger.end_step(
                step_idx,
                status="success",
                tokens=tokens,
                result_length=len(revised_article),
                details={
                    "issues_addressed": len(verdict.issues),
                    "new_word_count": word_count,
                    "model_used": model_name
                }
            )
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Writer",
                content=f"✅ Revision: {word_count} Wörter"
            )
            
            return revised_article
            
        except Exception as e:
            self.logger.end_step(step_idx, status="error", error=str(e))
            # Fallback: Original zurückgeben
            return self.article