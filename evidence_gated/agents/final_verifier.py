"""
Final Verifier Agent - Phase 8

Finale Prüfung und Bibliography-Erstellung.
"""

import re
from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import EvidencePack, Source


class FinalVerifierAgent(BaseAgent):
    """
    Phase 8: Final Verification
    
    Prüft Zitierfähigkeit und erstellt Bibliography.
    """
    
    def __init__(self, tier: str = "budget"):
        super().__init__(
            name="FinalVerifier",
            system_prompt="Du prüfst Artikel auf Zitierfähigkeit.",
            agent_type="editor",
            tier=tier,
            tools=[]
        )
    
    def verify_and_build_bibliography(
        self,
        article: str,
        evidence_packs: Dict[str, EvidencePack]
    ) -> Generator[AgentEvent, None, Dict[str, Any]]:
        """
        Finale Prüfung und Bibliography-Erstellung.
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content="📚 Erstelle Bibliography und finale Prüfung..."
        )
        
        # Alle Quellen sammeln
        all_sources: List[Source] = []
        for pack in evidence_packs.values():
            for source in pack.sources:
                all_sources.append(source)
        
        # Duplikate entfernen (nach URL)
        seen_urls = set()
        unique_sources = []
        for source in all_sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)
        
        # Bibliography erstellen (APA-Style)
        bibliography_entries = []
        for i, source in enumerate(unique_sources, 1):
            entry = self._format_apa(source, i)
            bibliography_entries.append(entry)
        
        bibliography_md = "## Literaturverzeichnis\n\n" + "\n".join(bibliography_entries)
        
        # Prüfungen
        issues = []
        
        # Prüfe ob alle Referenzen im Text vorhanden sind
        for i in range(1, len(unique_sources) + 1):
            if f"[{i}]" not in article:
                issues.append(f"Referenz [{i}] nicht im Text verwendet")
        
        # Prüfe auf Quellen ohne URL
        no_url_sources = [s for s in unique_sources if not s.url]
        if no_url_sources:
            issues.append(f"{len(no_url_sources)} Quellen ohne URL")
        
        # Independence Score berechnen
        publishers = set(s.publisher.lower() for s in unique_sources)
        independence_score = len(publishers) / len(unique_sources) if unique_sources else 0
        
        # Hersteller-Quote
        primary_count = len([s for s in unique_sources if s.source_class.value == "primary"])
        non_primary_rate = 1 - (primary_count / len(unique_sources)) if unique_sources else 0
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"✅ Bibliography: {len(unique_sources)} Quellen, "
                    f"Independence: {independence_score:.0%}, "
                    f"Nicht-Hersteller: {non_primary_rate:.0%}",
            data={
                "source_count": len(unique_sources),
                "independence_score": independence_score,
                "non_primary_rate": non_primary_rate,
                "issues": issues
            }
        )
        
        return {
            "bibliography_md": bibliography_md,
            "sources": [s.to_dict() for s in unique_sources],
            "source_count": len(unique_sources),
            "independence_score": independence_score,
            "non_primary_rate": non_primary_rate,
            "issues": issues,
            "passed": len(issues) == 0 and non_primary_rate >= 0.5
        }
    
    def _format_apa(self, source: Source, ref_num: int) -> str:
        """Formatiert eine Quelle im APA-Style."""
        author = source.author if source.author else source.publisher
        year = source.date[:4] if source.date else "o.D."
        title = source.title
        url = source.url
        
        return f"[{ref_num}] {author} ({year}). {title}. {url}"
