"""
Evidence Planner Agent - Phase 3

Plant die Recherche für alle B/C Claims.
Wählt passende Tools und erstellt Retrieval-Strategie.
"""

from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import (
    ClaimRegister, Claim, EvidenceClass, RetrievalTicket
)


class EvidencePlannerAgent(BaseAgent):
    """
    Phase 3: Evidence Planning
    
    Plant welche Tools für welche Claims verwendet werden.
    """
    
    # Tool-Mapping nach Claim-Typ und Thema
    TOOL_MAPPING = {
        "scientific": ["semantic_scholar", "arxiv"],
        "news": ["gnews", "tavily"],
        "tech": ["hackernews", "tavily"],
        "definitions": ["wikipedia", "tavily"],
        "government": ["ted", "tavily"],
        "general": ["tavily", "wikipedia"]
    }
    
    def __init__(self, tier: str = "budget"):
        super().__init__(
            name="EvidencePlanner",
            system_prompt="Du planst Recherche-Strategien für Claims.",
            agent_type="researcher",
            tier=tier,
            tools=[]
        )
    
    def plan_retrieval(
        self,
        claim_register: ClaimRegister
    ) -> Generator[AgentEvent, None, List[Dict[str, Any]]]:
        """
        Plant die Recherche für alle B/C Claims.
        
        Returns:
            Liste von Retrieval-Plänen mit Tool-Zuordnung
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="📋 Plane Recherche-Strategie..."
        )
        
        plans = []
        claims_needing_evidence = claim_register.get_claims_needing_evidence()
        
        for claim in claims_needing_evidence:
            if not claim.retrieval_ticket:
                continue
            
            # Tool basierend auf Claim-Inhalt wählen
            tool = self._select_tool_for_claim(claim, claim_register.term_map)
            
            # Queries mit TermMap-Varianten anreichern
            enriched_queries = self._enrich_queries(
                claim.retrieval_ticket.queries,
                claim_register.term_map
            )
            
            plan = {
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "evidence_class": claim.evidence_class.value,
                "tool": tool,
                "queries": enriched_queries,
                "min_sources": claim.min_sources,
                "excluded_domains": claim.retrieval_ticket.excluded_domains,
                "acceptance_criteria": claim.retrieval_ticket.acceptance_criteria
            }
            plans.append(plan)
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"✅ {len(plans)} Recherche-Pläne erstellt",
            data={"plans_count": len(plans)}
        )
        
        return plans
    
    def _select_tool_for_claim(self, claim: Claim, term_map) -> str:
        """Wählt das beste Tool für einen Claim."""
        claim_lower = claim.claim_text.lower()
        
        # Wissenschaftlich
        if any(kw in claim_lower for kw in ["studie", "forschung", "paper", "wissenschaft", "prozent"]):
            return "semantic_scholar"
        
        # KI/ML
        if any(kw in claim_lower for kw in ["ki", "ai", "machine learning", "neural", "llm", "gpt"]):
            return "arxiv"
        
        # Aktuelles/News
        if any(kw in claim_lower for kw in ["aktuell", "release", "version", "neu", "2024", "2025"]):
            return "gnews"
        
        # Tech-Meinungen
        if any(kw in claim_lower for kw in ["erfahrung", "vergleich", "alternative", "vs"]):
            return "hackernews"
        
        # Behörden
        if any(kw in claim_lower for kw in ["behörde", "verwaltung", "öffentlich", "rahmenvertrag"]):
            return "ted"
        
        # Definitionen
        if claim.claim_type.value == "definition":
            return "wikipedia"
        
        # Default
        return "tavily"
    
    def _enrich_queries(self, queries: List[str], term_map) -> List[str]:
        """Reichert Queries mit TermMap-Varianten an."""
        enriched = list(queries)
        
        # Füge Suchvarianten hinzu
        for query in queries:
            for term, variants in term_map.search_variants.items():
                if term.lower() in query.lower():
                    for variant in variants[:2]:  # Max 2 Varianten pro Term
                        new_query = query.replace(term, variant)
                        if new_query not in enriched:
                            enriched.append(new_query)
        
        return enriched[:5]  # Max 5 Queries pro Claim
