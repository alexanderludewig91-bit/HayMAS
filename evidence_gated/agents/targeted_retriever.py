"""
Targeted Retriever Agent - Phase 4

Führt gezielte Recherche für Claims durch.
Nutzt unsere bestehenden Tools (Tavily, Wikipedia, etc.)
"""

from typing import Dict, Any, Generator, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent, AgentEvent, EventType
from evidence_gated.models import (
    EvidencePack, Source, SourceClass, ClaimStatus
)
from mcp_server.server import get_mcp_server


class TargetedRetrieverAgent(BaseAgent):
    """
    Phase 4: Targeted Retrieval
    
    Führt gezielte Suchen für Claims durch.
    STOP-CONDITION: Stoppt wenn min_sources erfüllt.
    """
    
    MAX_SOURCES_PER_CLAIM = 6
    
    def __init__(self, tier: str = "budget"):
        super().__init__(
            name="TargetedRetriever",
            system_prompt="Du führst gezielte Recherchen durch.",
            agent_type="researcher",
            tier=tier,
            tools=["tavily_search", "wikipedia_search", "gnews_search", 
                   "hackernews_search", "semantic_scholar_search", "arxiv_search"]
        )
        self.mcp = get_mcp_server()
    
    def retrieve_for_claim(
        self,
        claim_id: str,
        claim_text: str,
        queries: List[str],
        tool: str,
        min_sources: int,
        excluded_domains: List[str] = None
    ) -> Generator[AgentEvent, None, EvidencePack]:
        """
        Recherchiert für einen einzelnen Claim.
        
        Args:
            claim_id: ID des Claims
            claim_text: Der Claim-Text
            queries: Suchqueries
            tool: Zu verwendendes Tool
            min_sources: Mindestanzahl Quellen
            excluded_domains: Auszuschließende Domains
        
        Returns:
            EvidencePack mit gefundenen Quellen
        """
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"🔍 Recherche für {claim_id}: {claim_text[:50]}..."
        )
        
        sources = []
        source_counter = 1
        
        # Iteriere durch Queries bis min_sources erfüllt
        for query in queries:
            if len(sources) >= min_sources:
                break
            
            if len(sources) >= self.MAX_SOURCES_PER_CLAIM:
                break
            
            yield AgentEvent(
                event_type=EventType.TOOL_CALL,
                agent_name=self.name,
                content=f"Query: {query}",
                data={"tool": tool, "query": query}
            )
            
            # Tool aufrufen
            tool_name = f"{tool}_search" if not tool.endswith("_search") else tool
            try:
                result = self.mcp.call_tool(tool_name, {"query": query, "max_results": 5})
                
                if result and result.get("results"):
                    for item in result["results"]:
                        # Domain-Filter
                        url = item.get("url", "")
                        if excluded_domains:
                            if any(d in url for d in excluded_domains):
                                continue
                        
                        # Source erstellen
                        source = Source(
                            source_id=f"S-{claim_id}-{source_counter:03d}",
                            title=item.get("title", "Unbekannt"),
                            publisher=self._extract_publisher(url),
                            url=url,
                            source_class=self._classify_source(url),
                            extract=item.get("snippet", item.get("content", ""))[:500],
                            supports_claims=[claim_id]
                        )
                        sources.append(source)
                        source_counter += 1
                        
                        if len(sources) >= self.MAX_SOURCES_PER_CLAIM:
                            break
                            
            except Exception as e:
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name=self.name,
                    content=f"Tool-Fehler: {e}"
                )
        
        # Status bestimmen
        status = ClaimStatus.FULFILLED if len(sources) >= min_sources else ClaimStatus.INSUFFICIENT
        
        evidence_pack = EvidencePack(
            claim_id=claim_id,
            sources=sources,
            status=status,
            notes=f"Gefunden: {len(sources)} von {min_sources} benötigten Quellen"
        )
        
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"{'✅' if status == ClaimStatus.FULFILLED else '⚠️'} {claim_id}: {len(sources)} Quellen",
            data={"sources_found": len(sources), "status": status.value}
        )
        
        return evidence_pack
    
    def _extract_publisher(self, url: str) -> str:
        """Extrahiert Publisher aus URL."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            # Entferne www. und .com/.de/etc
            domain = domain.replace("www.", "")
            parts = domain.split(".")
            if len(parts) >= 2:
                return parts[-2].title()
            return domain
        except:
            return "Unbekannt"
    
    def _classify_source(self, url: str) -> SourceClass:
        """Klassifiziert eine Quelle basierend auf URL."""
        url_lower = url.lower()
        
        # Primärquellen
        primary_domains = [
            "servicenow.com", "microsoft.com", "google.com", "aws.amazon.com",
            "gov.", ".gov", "europa.eu", "iso.org", "ieee.org"
        ]
        if any(d in url_lower for d in primary_domains):
            return SourceClass.PRIMARY
        
        # Sekundärquellen
        secondary_domains = [
            "gartner.com", "forrester.com", "mckinsey.com", "deloitte.com",
            "arxiv.org", "springer.com", "nature.com", "acm.org",
            "heise.de", "golem.de", "techcrunch.com", "zdnet.com"
        ]
        if any(d in url_lower for d in secondary_domains):
            return SourceClass.SECONDARY
        
        # Tertiär (Blogs, Foren)
        tertiary_domains = [
            "reddit.com", "medium.com", "dev.to", "hackernews",
            "stackoverflow.com", "quora.com"
        ]
        if any(d in url_lower for d in tertiary_domains):
            return SourceClass.TERTIARY
        
        # Default: Sekundär
        return SourceClass.SECONDARY
