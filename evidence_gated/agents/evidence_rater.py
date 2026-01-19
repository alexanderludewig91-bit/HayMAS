"""
Evidence Rater Agent - Phase 5

Bewertet Quellen nach 5 Dimensionen.
"""

import json
import re
from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import (
    EvidencePack, Source, SourceRating, ClaimStatus
)


EVIDENCE_RATER_PROMPT = """Du bist ein Evidence Rater Agent.

## DEINE AUFGABE
Bewerte jede Quelle nach 5 Dimensionen (0-3 Punkte je):

1. **Authority (0-3)**: Wie autoritativ ist die Quelle?
   - 3: Primärquelle (Hersteller, Behörde, Standard)
   - 2: Etablierte Fachmedien, Forschungsinstitute
   - 1: Bekannte Tech-Blogs, Nachrichtenportale
   - 0: Unbekannte Blogs, Foren, Social Media

2. **Independence (0-3)**: Wie unabhängig ist die Quelle?
   - 3: Völlig unabhängig vom Thema
   - 2: Branchenexperte, aber nicht Hersteller
   - 1: Hersteller-nah, Partner, Affiliate
   - 0: Hersteller selbst, PR-Material

3. **Recency (0-3)**: Wie aktuell ist die Quelle?
   - 3: < 6 Monate alt
   - 2: 6-12 Monate alt
   - 1: 1-3 Jahre alt
   - 0: > 3 Jahre alt oder kein Datum

4. **Specificity (0-3)**: Wie spezifisch belegt die Quelle den Claim?
   - 3: Exakte Aussage zum Claim
   - 2: Direkt relevante Information
   - 1: Nur Kontextinformation
   - 0: Kaum relevant

5. **Consensus (0-3)**: Wird die Aussage von anderen Quellen bestätigt?
   - 3: Mehrere unabhängige Quellen bestätigen
   - 2: Eine weitere Quelle bestätigt
   - 1: Keine Bestätigung, aber auch kein Widerspruch
   - 0: Andere Quellen widersprechen

## OUTPUT FORMAT
```json
{
  "ratings": [
    {
      "source_id": "S-001",
      "authority": 2,
      "independence": 1,
      "recency": 3,
      "specificity": 2,
      "consensus": 2,
      "reasoning": "Kurze Begründung"
    }
  ]
}
```

## MINDESTSCORE FÜR C-CLAIMS: 10 Punkte!
"""


class EvidenceRaterAgent(BaseAgent):
    """
    Phase 5: Evidence Rating
    
    Bewertet Quellen nach 5 Dimensionen.
    """
    
    MIN_SCORE_C_CLAIM = 10
    
    def __init__(self, tier: str = "budget"):
        super().__init__(
            name="EvidenceRater",
            system_prompt=EVIDENCE_RATER_PROMPT,
            agent_type="editor",  # Kritisches Denken wichtig
            tier=tier,
            tools=[]
        )
    
    def rate_evidence(
        self,
        evidence_pack: EvidencePack,
        claim_text: str
    ) -> Generator[AgentEvent, None, EvidencePack]:
        """
        Bewertet alle Quellen in einem EvidencePack.
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"⚖️ Bewerte Quellen für {evidence_pack.claim_id}..."
        )
        
        if not evidence_pack.sources:
            yield AgentEvent(
                event_type=EventType.STATUS,
                agent_name=self.name,
                content=f"⚠️ Keine Quellen zum Bewerten"
            )
            return evidence_pack
        
        # Quellen-Info für Prompt
        sources_info = "\n".join([
            f"- {s.source_id}: {s.title} ({s.publisher}, {s.url})\n  Extract: {s.extract[:200]}..."
            for s in evidence_pack.sources
        ])
        
        task = f"""Bewerte folgende Quellen für den Claim:

CLAIM: {claim_text}

QUELLEN:
{sources_info}

Bewerte jede Quelle nach den 5 Dimensionen. Antworte NUR mit JSON!"""

        result_text = ""
        for event in self.run(task):
            if event.event_type == EventType.RESPONSE:
                result_text = event.content
        
        # Ratings parsen und zuweisen
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text.strip()
            
            data = json.loads(json_str)
            
            for rating_data in data.get("ratings", []):
                source_id = rating_data.get("source_id")
                for source in evidence_pack.sources:
                    if source.source_id == source_id:
                        source.rating = SourceRating(
                            authority=rating_data.get("authority", 0),
                            independence=rating_data.get("independence", 0),
                            recency=rating_data.get("recency", 0),
                            specificity=rating_data.get("specificity", 0),
                            consensus=rating_data.get("consensus", 0)
                        )
                        break
        except:
            # Fallback: Automatische Bewertung basierend auf Source-Class
            for source in evidence_pack.sources:
                if source.source_class.value == "primary":
                    source.rating = SourceRating(authority=3, independence=0, recency=2, specificity=2, consensus=1)
                elif source.source_class.value == "secondary":
                    source.rating = SourceRating(authority=2, independence=2, recency=2, specificity=2, consensus=1)
                else:
                    source.rating = SourceRating(authority=1, independence=2, recency=2, specificity=1, consensus=1)
        
        # Durchschnittsscore berechnen
        scores = [s.rating.total for s in evidence_pack.sources if s.rating]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"✅ Bewertung abgeschlossen: Ø {avg_score:.1f} Punkte",
            data={"average_score": avg_score, "scores": scores}
        )
        
        return evidence_pack
