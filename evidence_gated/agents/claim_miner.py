"""
Claim Miner Agent - Phase 2

Das Herzstück des Evidence-Gated Systems.
Erzeugt Outline und ClaimRegister mit ZWANGSMECHANIK.
"""

import json
import re
from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import (
    QuestionBrief, TermMap, Outline, OutlineSection,
    Claim, ClaimType, EvidenceClass, SourceClass,
    RetrievalTicket, ClaimRegister
)


CLAIM_MINER_PROMPT = """Du bist ein Claim Miner Agent für Evidence-Gated Research.

## DEINE AUFGABE
Erstelle für die gegebene Frage:
1. **Outline**: Gliederung des Papers (für 10-15 Seiten)
2. **Claims**: Alle prüfbaren Aussagen die im Paper gemacht werden

## WAS IST EIN CLAIM?
Ein Claim ist eine PRÜFBARE Aussage. Typen:
- **definition**: "X ist ..." 
- **mechanism**: "X funktioniert so, dass ..."
- **comparison**: "X unterscheidet sich von Y durch ..."
- **effect**: "X führt typischerweise zu ..."
- **quant**: Zahlen, Prozent, Zeiten, Marktwerte
- **temporal**: "seit", "aktuell", "neu", "Stand ..."
- **normative**: "sollte", "empfohlen", "best practice"

## EVIDENZKLASSEN (KRITISCH!)
- **A - Stable Background**: Allgemeinwissen, stabil. KEINE Quelle nötig.
- **B - Source Recommended**: Fachliche Details. 1 gute Quelle.
- **C - Source Mandatory**: Volatile Fakten, Zahlen, aktuelle Events. MIND. 2 UNABHÄNGIGE Quellen!

## ZWANGSREGELN (MÜSSEN erfüllt sein!)
1. MINDESTENS 15 Claims insgesamt
2. MINDESTENS 5 C-Claims (quellenPFLICHTIG!)
3. JEDER B/C-Claim MUSS ein retrieval_ticket mit min. 2 Queries haben
4. Queries MÜSSEN die Suchvarianten aus der TermMap nutzen!

## OUTPUT FORMAT (NUR JSON!)

```json
{
  "outline": {
    "sections": [
      {
        "number": "1",
        "title": "Executive Summary",
        "goal": "Kernaussagen zusammenfassen",
        "expected_claim_ids": ["C-01", "C-02"],
        "estimated_pages": 1.0
      }
    ],
    "total_estimated_pages": 12
  },
  "claims": [
    {
      "claim_id": "C-01",
      "claim_text": "Die präzise, prüfbare Aussage",
      "claim_type": "definition|mechanism|comparison|effect|quant|temporal|normative",
      "evidence_class": "A|B|C",
      "freshness_required": false,
      "recency_days": null,
      "required_source_classes": ["primary", "secondary"],
      "section_id": "1",
      "retrieval_ticket": {
        "queries": ["Suchquery 1", "Suchquery 2 (Variante)"],
        "preferred_domains": [],
        "excluded_domains": [],
        "min_sources": 2,
        "independence_rule": "different_publishers",
        "primary_required": false,
        "recency_days": null,
        "acceptance_criteria": "Quelle muss X explizit erwähnen"
      }
    }
  ]
}
```

## BEISPIEL FÜR GUTE CLAIMS

Frage: "Was ist ServiceNow Build Agent?"

GUTE Claims:
- C-01 (definition, A): "ServiceNow ist eine Enterprise-Plattform für digitale Workflows"
- C-02 (definition, B): "Build Agent ist ein Feature zur KI-gestützten Anwendungsentwicklung"
- C-03 (temporal, C): "Build Agent wurde im Release [VERSION] [DATUM] eingeführt" 
- C-04 (mechanism, B): "Build Agent nutzt generative KI zur Code-Generierung"
- C-05 (quant, C): "Build Agent kann Entwicklungszeit um X% reduzieren"
- C-06 (comparison, C): "Build Agent unterscheidet sich von klassischer Low-Code-Entwicklung durch..."

SCHLECHTE Claims (zu vage):
- "Build Agent ist nützlich" (nicht prüfbar)
- "ServiceNow ist gut" (nicht prüfbar)

## QUALITÄTSKRITERIEN
- Claims müssen SPEZIFISCH und PRÜFBAR sein
- Jeder Claim muss einer Outline-Section zugeordnet sein
- C-Claims sollten aktuelle/volatile Informationen betreffen
- Retrieval-Queries müssen verschiedene Suchwinkel abdecken
"""


class ClaimMinerAgent(BaseAgent):
    """
    Phase 2: Claim Mining
    
    Erzeugt Outline und ClaimRegister mit Zwangsmechanik.
    """
    
    # Zwangsregeln
    MIN_TOTAL_CLAIMS = 15
    MIN_C_CLAIMS = 5
    MIN_QUERIES_PER_CLAIM = 2
    
    def __init__(self, tier: str = "premium"):
        super().__init__(
            name="ClaimMiner",
            system_prompt=CLAIM_MINER_PROMPT,
            agent_type="orchestrator",  # Kritisches Denken wichtig
            tier=tier,
            tools=[]
        )
    
    def mine_claims(
        self,
        question_brief: QuestionBrief,
        term_map: TermMap
    ) -> Generator[AgentEvent, None, ClaimRegister]:
        """
        Erzeugt Outline und Claims für die gegebene Frage.
        
        Args:
            question_brief: Präzisierte Fragestellung
            term_map: Terminologie-Mapping
        
        Yields:
            AgentEvents
        
        Returns:
            ClaimRegister mit Outline und Claims
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="⛏️ Mining Claims aus Fragestellung..."
        )
        
        # Suchvarianten für den Prompt aufbereiten
        search_variants_str = "\n".join([
            f"- {term}: {', '.join(variants)}"
            for term, variants in term_map.search_variants.items()
        ])
        
        task = f"""Erstelle Outline und Claims für folgende Frage:

## QUESTION BRIEF
- Kernfrage: {question_brief.core_question}
- Zielgruppe: {question_brief.audience}
- Ton: {question_brief.tone}
- Ziel-Seiten: {question_brief.target_pages}
- Freshness: {question_brief.freshness_priority}
- Stand: {question_brief.as_of_date}
- Scope IN: {', '.join(question_brief.scope_in) if question_brief.scope_in else 'nicht definiert'}
- Scope OUT: {', '.join(question_brief.scope_out) if question_brief.scope_out else 'nicht definiert'}

## TERM MAP (NUTZE DIESE FÜR QUERIES!)
Kanonische Begriffe: {', '.join(term_map.canonical_terms)}
Synonyme: {json.dumps(term_map.synonyms, ensure_ascii=False)}
Negative Keywords (AUSSCHLIESSEN!): {', '.join(term_map.negative_keywords)}
Disambiguation: {'; '.join(term_map.disambiguation_notes)}

Suchvarianten (NUTZE DIESE!):
{search_variants_str}

## ZWANGSREGELN (MÜSSEN erfüllt sein!)
- MINDESTENS {self.MIN_TOTAL_CLAIMS} Claims
- MINDESTENS {self.MIN_C_CLAIMS} C-Claims
- JEDER B/C-Claim braucht {self.MIN_QUERIES_PER_CLAIM}+ Queries

Antworte NUR mit dem JSON-Objekt!"""

        result_text = ""
        for event in self.run(task):
            yield event
            if event.event_type == EventType.RESPONSE:
                result_text = event.content
        
        # JSON parsen
        claim_register = self._parse_and_validate(
            result_text, question_brief, term_map
        )
        
        # Validierung
        validation = claim_register.validate()
        
        if validation["valid"]:
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"✅ ClaimRegister erstellt: {validation['stats']['total_claims']} Claims "
                        f"(A:{validation['stats']['a_claims']}, B:{validation['stats']['b_claims']}, "
                        f"C:{validation['stats']['c_claims']})",
                data=validation
            )
        else:
            yield AgentEvent(
                event_type=EventType.ERROR,
                agent_name=self.name,
                content=f"⚠️ ClaimRegister hat Probleme: {'; '.join(validation['issues'])}",
                data=validation
            )
        
        return claim_register
    
    def _parse_and_validate(
        self,
        result_text: str,
        question_brief: QuestionBrief,
        term_map: TermMap
    ) -> ClaimRegister:
        """Parst das JSON und erstellt ClaimRegister."""
        try:
            # JSON extrahieren
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text.strip()
            
            data = json.loads(json_str)
            
            # Outline parsen
            outline = Outline.from_dict(data.get("outline", {"sections": []}))
            
            # Claims parsen
            claims = []
            for claim_data in data.get("claims", []):
                # Retrieval Ticket
                ticket_data = claim_data.get("retrieval_ticket")
                ticket = None
                if ticket_data:
                    ticket = RetrievalTicket(
                        queries=ticket_data.get("queries", []),
                        preferred_domains=ticket_data.get("preferred_domains", []),
                        excluded_domains=ticket_data.get("excluded_domains", []),
                        min_sources=ticket_data.get("min_sources", 1),
                        independence_rule=ticket_data.get("independence_rule", "different_publishers"),
                        primary_required=ticket_data.get("primary_required", False),
                        recency_days=ticket_data.get("recency_days"),
                        acceptance_criteria=ticket_data.get("acceptance_criteria", "")
                    )
                
                # Source Classes parsen
                source_classes = []
                for sc in claim_data.get("required_source_classes", []):
                    try:
                        source_classes.append(SourceClass(sc))
                    except ValueError:
                        pass
                
                claim = Claim(
                    claim_id=claim_data.get("claim_id", f"C-{len(claims)+1:02d}"),
                    claim_text=claim_data.get("claim_text", ""),
                    claim_type=ClaimType(claim_data.get("claim_type", "definition")),
                    evidence_class=EvidenceClass(claim_data.get("evidence_class", "B")),
                    freshness_required=claim_data.get("freshness_required", False),
                    recency_days=claim_data.get("recency_days"),
                    required_source_classes=source_classes,
                    retrieval_ticket=ticket,
                    section_id=claim_data.get("section_id", "")
                )
                claims.append(claim)
            
            return ClaimRegister(
                question_brief=question_brief,
                term_map=term_map,
                outline=outline,
                claims=claims,
                min_total_claims=self.MIN_TOTAL_CLAIMS,
                min_c_claims=self.MIN_C_CLAIMS
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback mit leeren Claims
            return ClaimRegister(
                question_brief=question_brief,
                term_map=term_map,
                outline=Outline(sections=[]),
                claims=[],
                min_total_claims=self.MIN_TOTAL_CLAIMS,
                min_c_claims=self.MIN_C_CLAIMS
            )
