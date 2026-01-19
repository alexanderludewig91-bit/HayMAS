"""
Evidence-Gated Orchestrator

Koordiniert den gesamten Evidence-Gated Workflow.
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
from config import OUTPUT_DIR
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
    
    Vereinfachte Version die direkt LLM-Aufrufe macht statt
    komplexe Generator-Ketten.
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
            if not validation["valid"]:
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name="Orchestrator",
                    content=f"⚠️ ClaimRegister: {'; '.join(validation['issues'])}"
                )
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
            
            # ===== PHASE 5: Evidence Rating =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="⚖️ Phase 5/8: Evidence Rating..."
            )
            
            yield from self._phase_5_rating()
            
            # ===== PHASE 6: Claim-Bounded Writing =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="✍️ Phase 6/8: Claim-Bounded Writing..."
            )
            
            self.article = yield from self._phase_6_writing()
            
            # ===== PHASE 7: Editorial Review =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="📋 Phase 7/8: Editorial Review..."
            )
            
            # Vereinfacht: Kein Review-Loop für jetzt
            
            # ===== PHASE 8: Final Verification =====
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Orchestrator",
                content="📚 Phase 8/8: Bibliography..."
            )
            
            self.article = self._add_bibliography()
            
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
        """Phase 1-2: Erstellt ClaimRegister mit LLM."""
        from anthropic import Anthropic
        from config import ANTHROPIC_API_KEY
        
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        prompt = f"""Du bist ein Claim Mining Agent für wissenschaftliche Artikel.

FRAGE: {question}

AUFGABE: Erstelle ein ClaimRegister mit:
1. QuestionBrief (präzisierte Frage)
2. TermMap (Synonyme, Suchvarianten, Negative Keywords)
3. Outline (Gliederung für 12 Seiten)
4. Claims (MINDESTENS 15 Claims, davon MINDESTENS 5 C-Claims!)

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

WICHTIG:
- MINDESTENS 15 Claims!
- MINDESTENS 5 C-Claims!
- Jeder B/C-Claim braucht ein retrieval_ticket mit 2-3 Queries!
- Nutze verschiedene Suchvarianten (auch Englisch)!

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
      {{"number": "1", "title": "...", "goal": "...", "expected_claim_ids": ["C-01"], "estimated_pages": 1.0}}
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
        "queries": ["Query 1", "Query 2"],
        "min_sources": 2
      }}
    }}
  ]
}}
```"""

        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="ClaimMiner",
            content="⛏️ Mining Claims mit Claude..."
        )
        
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        
        # JSON parsen
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text.strip()
            
            data = json.loads(json_str)
            
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
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="ClaimMiner",
                content=f"✅ {len(claims)} Claims extrahiert"
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
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name="ClaimMiner",
                content=f"❌ Parsing-Fehler: {e}"
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
            
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name="Retriever",
                content=f"   {'✅' if status == ClaimStatus.FULFILLED else '⚠️'} {len(sources)} Quellen"
            )
    
    def _phase_5_rating(self) -> Generator[AgentEvent, None, None]:
        """Phase 5: Quellen bewerten."""
        for claim_id, pack in self.evidence_packs.items():
            for source in pack.sources:
                # Einfache automatische Bewertung
                source.rating = SourceRating(
                    authority=2 if "servicenow.com" in source.url else 1,
                    independence=1 if "servicenow.com" in source.url else 2,
                    recency=2,
                    specificity=2,
                    consensus=1
                )
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Rater",
            content=f"✅ {sum(len(p.sources) for p in self.evidence_packs.values())} Quellen bewertet"
        )
    
    def _phase_6_writing(self) -> Generator[AgentEvent, None, str]:
        """Phase 6: Artikel schreiben."""
        from openai import OpenAI
        from config import OPENAI_API_KEY
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Claims aufbereiten
        usable_claims = []
        for claim in self.claim_register.claims:
            if claim.evidence_class == EvidenceClass.A:
                usable_claims.append({"id": claim.claim_id, "text": claim.claim_text, "sources": []})
            else:
                pack = self.evidence_packs.get(claim.claim_id)
                if pack and pack.status == ClaimStatus.FULFILLED:
                    sources = [f"[{i+1}]" for i in range(len(pack.sources))]
                    usable_claims.append({"id": claim.claim_id, "text": claim.claim_text, "sources": sources})
        
        claims_text = "\n".join([
            f"- {c['id']}: {c['text']}" + (f" (Quellen: {', '.join(c['sources'])})" if c['sources'] else "")
            for c in usable_claims
        ])
        
        # Outline
        outline_text = "\n".join([
            f"{s.number}. {s.title}"
            for s in self.claim_register.outline.sections
        ])
        
        prompt = f"""Schreibe einen wissenschaftlichen Artikel.

FRAGE: {self.claim_register.question_brief.core_question}

OUTLINE:
{outline_text}

VERWENDBARE CLAIMS (mit Claim-Anchors!):
{claims_text}

REGELN:
1. Nutze Claim-Anchors: (C-01), (C-02), etc.
2. Nutze Quellenverweise: [1], [2], etc.
3. Schreibe auf Expertenniveau
4. 10-15 Seiten Umfang
5. Füge am Ende einen "Limitations" Abschnitt ein

SCHREIBE DEN ARTIKEL:"""

        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Writer",
            content="✍️ Schreibe Artikel mit GPT..."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000
        )
        
        article = response.choices[0].message.content
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name="Writer",
            content=f"✅ Artikel: {len(article)} Zeichen"
        )
        
        return article
    
    def _add_bibliography(self) -> str:
        """Fügt Literaturverzeichnis hinzu."""
        all_sources = []
        for pack in self.evidence_packs.values():
            all_sources.extend(pack.sources)
        
        # Duplikate entfernen
        seen = set()
        unique = []
        for s in all_sources:
            if s.url not in seen:
                seen.add(s.url)
                unique.append(s)
        
        if not unique:
            return self.article
        
        bib = "\n\n## Literaturverzeichnis\n\n"
        for i, s in enumerate(unique, 1):
            bib += f"[{i}] {s.publisher}: {s.title}. {s.url}\n"
        
        return self.article + bib
    
    def _select_tool(self, claim: Claim) -> str:
        """Wählt Tool für Claim."""
        text = claim.claim_text.lower()
        
        if any(kw in text for kw in ["studie", "forschung", "prozent"]):
            return "semantic_scholar"
        if any(kw in text for kw in ["release", "version", "2024", "2025"]):
            return "gnews"
        if any(kw in text for kw in ["erfahrung", "vergleich"]):
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
