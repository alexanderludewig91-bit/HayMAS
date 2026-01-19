"""
Claim-Bounded Writer Agent - Phase 6

Schreibt den Artikel STRIKT basierend auf Claims.
Jede Aussage muss einen Claim-Anchor haben.
"""

import json
from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import (
    ClaimRegister, EvidencePack, Claim, EvidenceClass
)


CLAIM_BOUNDED_WRITER_PROMPT = """Du bist ein Claim-Bounded Writer Agent.

## DEINE AUFGABE
Schreibe einen wissenschaftlichen Artikel basierend auf dem ClaimRegister und den EvidencePacks.

## KRITISCHE REGELN
1. **NUR Claims mit Evidenz verwenden!**
   - A-Claims: Dürfen ohne Quelle verwendet werden
   - B/C-Claims: NUR wenn EvidencePack mit Status "fulfilled" existiert!

2. **Claim-Anchors setzen!**
   - Jede wichtige Aussage bekommt einen Claim-Anchor: (C-01), (C-02), etc.
   - Das macht den Text nachprüfbar!

3. **Quellenverweise!**
   - Nutze Fußnoten-Format: [1], [2], etc.
   - Am Ende: Vollständiges Literaturverzeichnis

## STRUKTUR
1. Executive Summary (max 1 Seite)
2. Hauptteil (gem. Outline)
3. Implikationen / Empfehlungen
4. Limitations (explizit!)
5. Literaturverzeichnis

## BEISPIEL

"ServiceNow ist eine Enterprise-Plattform für digitale Workflows (C-01). 
Das Build Agent Feature wurde im Vancouver Release 2024 eingeführt (C-03) [1].
Laut einer Studie von Gartner kann es die Entwicklungszeit um bis zu 40% reduzieren (C-05) [2][3]."

## Literaturverzeichnis
[1] ServiceNow (2024): Vancouver Release Notes. https://...
[2] Gartner (2024): Low-Code Market Analysis. https://...
[3] Forrester (2024): ServiceNow Wave Report. https://...

## QUALITÄTSKRITERIEN
- KEINE Aussagen ohne Claim-Anchor (außer Übergänge/Einleitungen)
- ALLE C-Claims müssen Quellen haben
- Wissenschaftlicher, sachlicher Stil
- 10-15 Seiten Zielumfang
"""


class ClaimBoundedWriterAgent(BaseAgent):
    """
    Phase 6: Claim-Bounded Writing
    
    Schreibt STRIKT basierend auf Claims und Evidenz.
    """
    
    def __init__(self, tier: str = "premium"):
        super().__init__(
            name="ClaimBoundedWriter",
            system_prompt=CLAIM_BOUNDED_WRITER_PROMPT,
            agent_type="writer",
            tier=tier,
            tools=[]
        )
    
    def write_article(
        self,
        claim_register: ClaimRegister,
        evidence_packs: Dict[str, EvidencePack]
    ) -> Generator[AgentEvent, None, str]:
        """
        Schreibt den Artikel basierend auf Claims und Evidenz.
        
        Args:
            claim_register: Das ClaimRegister mit allen Claims
            evidence_packs: Dict von claim_id -> EvidencePack
        
        Returns:
            Der fertige Artikel als Markdown
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="✍️ Schreibe Artikel basierend auf Claims und Evidenz..."
        )
        
        # Claims mit Status aufbereiten
        claims_info = []
        sources_list = []
        source_counter = 1
        
        for claim in claim_register.claims:
            evidence = evidence_packs.get(claim.claim_id)
            
            claim_info = {
                "id": claim.claim_id,
                "text": claim.claim_text,
                "type": claim.claim_type.value,
                "evidence_class": claim.evidence_class.value,
                "section": claim.section_id,
                "usable": True,
                "sources": []
            }
            
            if claim.evidence_class in [EvidenceClass.B, EvidenceClass.C]:
                if evidence and evidence.status.value == "fulfilled":
                    for source in evidence.sources:
                        source_ref = f"[{source_counter}]"
                        claim_info["sources"].append(source_ref)
                        sources_list.append({
                            "ref": source_ref,
                            "title": source.title,
                            "publisher": source.publisher,
                            "url": source.url,
                            "date": source.date
                        })
                        source_counter += 1
                else:
                    claim_info["usable"] = False
                    claim_info["reason"] = "Keine ausreichende Evidenz"
            
            claims_info.append(claim_info)
        
        # Outline aufbereiten
        outline_info = "\n".join([
            f"{s.number}. {s.title} (Claims: {', '.join(s.expected_claim_ids)})"
            for s in claim_register.outline.sections
        ])
        
        # Claims aufbereiten
        usable_claims = [c for c in claims_info if c["usable"]]
        unusable_claims = [c for c in claims_info if not c["usable"]]
        
        claims_text = "\n".join([
            f"- {c['id']} ({c['evidence_class']}): {c['text']}"
            + (f" → Quellen: {', '.join(c['sources'])}" if c['sources'] else "")
            for c in usable_claims
        ])
        
        # Quellen aufbereiten
        sources_text = "\n".join([
            f"{s['ref']} {s['publisher']} ({s['date'] or 'o.D.'}): {s['title']}. {s['url']}"
            for s in sources_list
        ])
        
        task = f"""Schreibe einen wissenschaftlichen Artikel.

## FRAGE
{claim_register.question_brief.core_question}

## ZIELGRUPPE & TON
- Zielgruppe: {claim_register.question_brief.audience}
- Ton: {claim_register.question_brief.tone}
- Ziel-Seiten: {claim_register.question_brief.target_pages}

## OUTLINE
{outline_info}

## VERWENDBARE CLAIMS (mit Claim-Anchors!)
{claims_text}

## NICHT VERWENDBARE CLAIMS (zu wenig Evidenz!)
{', '.join([c['id'] for c in unusable_claims]) if unusable_claims else 'Keine'}

## VERFÜGBARE QUELLEN
{sources_text if sources_text else 'Keine Quellen verfügbar'}

## ANWEISUNGEN
1. Folge der Outline-Struktur
2. Verwende NUR die verwendbaren Claims
3. Setze Claim-Anchors: (C-01), (C-02), etc.
4. Setze Quellenverweise: [1], [2], etc.
5. Füge am Ende das Literaturverzeichnis ein
6. Füge einen "Limitations" Abschnitt ein

SCHREIBE JETZT DEN ARTIKEL:"""

        article = ""
        for event in self.run(task):
            yield event
            if event.event_type == EventType.RESPONSE:
                article = event.content
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"✅ Artikel geschrieben: {len(article)} Zeichen",
            data={"length": len(article), "claims_used": len(usable_claims)}
        )
        
        return article
