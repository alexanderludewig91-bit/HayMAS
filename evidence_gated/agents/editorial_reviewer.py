"""
Editorial Reviewer Agent - Phase 7

Prüft Claim Coverage und Evidenzqualität.
Identifiziert "Hallucination Surface".
"""

import json
import re
from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import (
    ClaimRegister, EvidencePack, ReviewReport, ReviewIssue, EvidenceClass
)


EDITORIAL_REVIEWER_PROMPT = """Du bist ein Editorial Reviewer Agent.

## DEINE AUFGABE
Prüfe den Artikel auf:
1. **Claim Coverage**: Werden alle Claims im Text verwendet?
2. **Evidence Sufficiency**: Sind alle C-Claims mit Quellen belegt?
3. **Hallucination Surface**: Gibt es Aussagen OHNE Claim-Anchor?
4. **Contradictions**: Widersprechen sich Quellen?
5. **Stil/Klarheit**: Erst nach den evidenzbasierten Checks

## OUTPUT FORMAT
```json
{
  "claim_coverage": {
    "total_claims": 15,
    "claims_in_text": 12,
    "missing_claims": ["C-05", "C-08", "C-12"]
  },
  "evidence_sufficiency": {
    "c_claims_total": 5,
    "c_claims_with_sources": 4,
    "insufficient_claims": [
      {"claim_id": "C-07", "reason": "Nur 1 Quelle, braucht 2"}
    ]
  },
  "hallucination_surface": {
    "count": 2,
    "unanchored_statements": [
      "Die Entwicklungszeit reduziert sich um 50%",
      "ServiceNow ist Marktführer"
    ]
  },
  "contradictions": [],
  "style_issues": ["Abschnitt 3 ist zu lang", "Fazit fehlt"],
  "verdict": {
    "passed": false,
    "needs_gap_loop": true,
    "gap_claims": ["C-07"],
    "summary": "Artikel gut, aber C-07 braucht mehr Evidenz"
  }
}
```

## KRITISCHE PRÜFUNGEN
1. **ALLE C-Claims MÜSSEN Quellenverweise haben!**
2. **Aussagen ohne (C-XX) Anchor sind Halluzinationen!**
3. **Zahlen/Prozente MÜSSEN belegbar sein!**
"""


class EditorialReviewerAgent(BaseAgent):
    """
    Phase 7: Editorial Review
    
    Prüft Claim Coverage, Evidenz und Halluzinationen.
    """
    
    def __init__(self, tier: str = "premium"):
        super().__init__(
            name="EditorialReviewer",
            system_prompt=EDITORIAL_REVIEWER_PROMPT,
            agent_type="editor",
            tier=tier,
            tools=[]
        )
    
    def review_article(
        self,
        article: str,
        claim_register: ClaimRegister,
        evidence_packs: Dict[str, EvidencePack]
    ) -> Generator[AgentEvent, None, ReviewReport]:
        """
        Prüft den Artikel auf Claim Coverage und Qualität.
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="📋 Prüfe Artikel auf Claim Coverage und Halluzinationen..."
        )
        
        # Claims-Info aufbereiten
        claims_info = "\n".join([
            f"- {c.claim_id} ({c.evidence_class.value}): {c.claim_text}"
            for c in claim_register.claims
        ])
        
        # C-Claims mit Evidenz-Status
        c_claims_status = []
        for claim in claim_register.get_c_claims():
            evidence = evidence_packs.get(claim.claim_id)
            status = evidence.status.value if evidence else "missing"
            c_claims_status.append(f"{claim.claim_id}: {status}")
        
        task = f"""Prüfe folgenden Artikel:

## ARTIKEL
{article[:15000]}

## CLAIMS (müssen im Artikel vorkommen!)
{claims_info}

## C-CLAIMS MIT EVIDENZ-STATUS
{chr(10).join(c_claims_status)}

Führe die Prüfung durch und antworte NUR mit JSON!"""

        result_text = ""
        for event in self.run(task):
            if event.event_type == EventType.RESPONSE:
                result_text = event.content
        
        # ReviewReport erstellen
        report = self._parse_review(result_text, claim_register, evidence_packs)
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"{'✅' if report.passed else '⚠️'} Review: "
                    f"Coverage {report.claim_coverage_rate:.0%}, "
                    f"Halluzinationen: {report.hallucination_count}",
            data=report.to_dict()
        )
        
        return report
    
    def _parse_review(
        self,
        result_text: str,
        claim_register: ClaimRegister,
        evidence_packs: Dict[str, EvidencePack]
    ) -> ReviewReport:
        """Parst das Review-Ergebnis."""
        report = ReviewReport(
            total_claims=len(claim_register.claims),
            c_claims_total=len(claim_register.get_c_claims())
        )
        
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text.strip()
            
            data = json.loads(json_str)
            
            # Claim Coverage
            coverage = data.get("claim_coverage", {})
            report.claims_in_text = coverage.get("claims_in_text", 0)
            
            # Evidence Sufficiency
            evidence = data.get("evidence_sufficiency", {})
            report.c_claims_with_evidence = evidence.get("c_claims_with_sources", 0)
            
            # Hallucination Surface
            hallucination = data.get("hallucination_surface", {})
            report.unanchored_statements = hallucination.get("unanchored_statements", [])
            
            # Issues erstellen
            for insufficient in evidence.get("insufficient_claims", []):
                report.issues.append(ReviewIssue(
                    issue_type="uncovered_claim",
                    severity="critical",
                    description=insufficient.get("reason", "Unzureichende Evidenz"),
                    claim_id=insufficient.get("claim_id")
                ))
            
            for statement in report.unanchored_statements:
                report.issues.append(ReviewIssue(
                    issue_type="hallucination",
                    severity="major",
                    description=f"Aussage ohne Claim-Anchor: {statement[:50]}..."
                ))
            
            # Verdict
            verdict = data.get("verdict", {})
            report.passed = verdict.get("passed", False)
            report.needs_gap_loop = verdict.get("needs_gap_loop", False)
            report.gap_claims = verdict.get("gap_claims", [])
            
        except:
            # Fallback: Einfache Analyse
            report.claims_in_text = sum(
                1 for c in claim_register.claims 
                if f"({c.claim_id})" in result_text or c.claim_id in result_text
            )
            report.c_claims_with_evidence = len([
                c for c in claim_register.get_c_claims()
                if evidence_packs.get(c.claim_id) and 
                evidence_packs[c.claim_id].status.value == "fulfilled"
            ])
            report.passed = (
                report.c_claims_with_evidence == report.c_claims_total and
                report.hallucination_count == 0
            )
        
        return report
