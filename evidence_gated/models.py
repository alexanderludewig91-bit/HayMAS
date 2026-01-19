"""
Evidence-Gated System - Datenmodelle

Alle Artefakte des Evidence-Gated Workflows:
- QuestionBrief, TermMap (Phase 1)
- Outline, ClaimRegister (Phase 2)
- RetrievalTicket (Phase 3)
- EvidencePack, SourceRating (Phase 4-5)
- ReviewReport (Phase 7)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import date
import json


# =============================================================================
# ENUMS
# =============================================================================

class ClaimType(Enum):
    """Typen von Claims nach dem Design-Dokument."""
    DEFINITION = "definition"      # "X ist ..."
    MECHANISM = "mechanism"        # "X funktioniert so, dass ..."
    COMPARISON = "comparison"      # "X unterscheidet sich von Y durch ..."
    EFFECT = "effect"              # "X führt typischerweise zu ..."
    QUANTITATIVE = "quant"         # Zahlen, Prozent, Zeiten, Marktwerte
    TEMPORAL = "temporal"          # "seit", "aktuell", "neu", "Stand ..."
    NORMATIVE = "normative"        # "sollte", "empfohlen", "best practice"


class EvidenceClass(Enum):
    """
    Evidenzklassen A/B/C - definieren Quellenanforderungen.
    
    A - Stable Background: Kein Quelle erforderlich
    B - Source Recommended: 1 gute Quelle reicht
    C - Source Mandatory: Mind. 2 unabhängige Quellen
    """
    A = "A"  # Stable Background - keine Quelle nötig
    B = "B"  # Source Recommended - 1 Quelle
    C = "C"  # Source Mandatory - 2+ unabhängige Quellen


class SourceClass(Enum):
    """Quellenklassen für Priorisierung."""
    PRIMARY = "primary"      # Hersteller, Standard, Norm, Behörde
    SECONDARY = "secondary"  # Fachmedien, Institute, Peer-Review
    TERTIARY = "tertiary"    # HN, Reddit, Blogs (nur Praxisindikator!)


class ClaimStatus(Enum):
    """Status eines Claims im Workflow."""
    PENDING = "pending"          # Noch nicht recherchiert
    IN_PROGRESS = "in_progress"  # Recherche läuft
    FULFILLED = "fulfilled"      # Evidenzanforderung erfüllt
    INSUFFICIENT = "insufficient"  # Nicht genug Quellen
    CONFLICT = "conflict"        # Widersprüchliche Quellen


# =============================================================================
# PHASE 1: QUERY NORMALIZATION
# =============================================================================

@dataclass
class QuestionBrief:
    """
    Präzisierte Fragestellung mit Scope-Definition.
    Output von Phase 1.
    """
    core_question: str              # Kernfrage (präzisiert)
    original_question: str          # Ursprüngliche User-Frage
    audience: str                   # Zielpublikum (z.B. "Fachexperten", "Management")
    tone: str                       # Ton (z.B. "wissenschaftlich", "praxisorientiert")
    target_pages: int = 12          # Ziel-Seitenzahl (10-15)
    as_of_date: str = ""            # Stand-Datum (YYYY-MM-DD)
    freshness_priority: str = "medium"  # high/medium/low
    scope_in: List[str] = field(default_factory=list)   # Was ist im Scope
    scope_out: List[str] = field(default_factory=list)  # Was ist explizit ausgeschlossen
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_question": self.core_question,
            "original_question": self.original_question,
            "audience": self.audience,
            "tone": self.tone,
            "target_pages": self.target_pages,
            "as_of_date": self.as_of_date,
            "freshness_priority": self.freshness_priority,
            "scope_in": self.scope_in,
            "scope_out": self.scope_out
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "QuestionBrief":
        return cls(**data)


@dataclass
class TermMap:
    """
    Terminologie-Mapping für präzise Suchen.
    Löst das "Agent Builder vs Build Agent" Problem!
    """
    canonical_terms: List[str]           # Kanonische Begriffe
    synonyms: Dict[str, List[str]]       # Term -> Synonyme
    negative_keywords: List[str]         # Zu vermeidende Treffer
    disambiguation_notes: List[str]      # Klärungen (z.B. "Produkt vs. Feature")
    search_variants: Dict[str, List[str]]  # Term -> Suchvarianten (3-5 pro Term)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_terms": self.canonical_terms,
            "synonyms": self.synonyms,
            "negative_keywords": self.negative_keywords,
            "disambiguation_notes": self.disambiguation_notes,
            "search_variants": self.search_variants
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TermMap":
        return cls(**data)
    
    def get_all_search_terms(self, canonical_term: str) -> List[str]:
        """Gibt alle Suchvarianten für einen kanonischen Term zurück."""
        terms = [canonical_term]
        terms.extend(self.synonyms.get(canonical_term, []))
        terms.extend(self.search_variants.get(canonical_term, []))
        return list(set(terms))


# =============================================================================
# PHASE 2: OUTLINE & CLAIMS
# =============================================================================

@dataclass
class OutlineSection:
    """Ein Abschnitt im Outline."""
    number: str                    # z.B. "1", "2.1"
    title: str                     # Abschnittstitel
    goal: str                      # Was soll dieser Abschnitt erreichen?
    expected_claim_ids: List[str]  # Welche Claims gehören hierher?
    estimated_pages: float = 1.0   # Geschätzte Seitenzahl


@dataclass
class Outline:
    """Gliederung des Papers."""
    sections: List[OutlineSection]
    total_estimated_pages: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sections": [
                {
                    "number": s.number,
                    "title": s.title,
                    "goal": s.goal,
                    "expected_claim_ids": s.expected_claim_ids,
                    "estimated_pages": s.estimated_pages
                }
                for s in self.sections
            ],
            "total_estimated_pages": self.total_estimated_pages
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Outline":
        sections = [
            OutlineSection(**s) for s in data.get("sections", [])
        ]
        return cls(
            sections=sections,
            total_estimated_pages=data.get("total_estimated_pages", 0)
        )


@dataclass
class RetrievalTicket:
    """
    Recherche-Auftrag für einen B/C-Claim.
    Definiert WAS gesucht werden soll und WANN es erfüllt ist.
    """
    queries: List[str]                    # Suchqueries (mit Varianten)
    preferred_domains: List[str] = field(default_factory=list)
    excluded_domains: List[str] = field(default_factory=list)
    min_sources: int = 1
    independence_rule: str = "different_publishers"  # oder "any"
    primary_required: bool = False
    recency_days: Optional[int] = None    # Falls Freshness wichtig
    acceptance_criteria: str = ""         # Was muss die Quelle enthalten?
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "queries": self.queries,
            "preferred_domains": self.preferred_domains,
            "excluded_domains": self.excluded_domains,
            "min_sources": self.min_sources,
            "independence_rule": self.independence_rule,
            "primary_required": self.primary_required,
            "recency_days": self.recency_days,
            "acceptance_criteria": self.acceptance_criteria
        }


@dataclass
class Claim:
    """
    Ein einzelner Claim - das Herzstück des Systems.
    Jede prüfbare Aussage im Paper ist ein Claim.
    """
    claim_id: str                         # z.B. "C-01"
    claim_text: str                       # Die eigentliche Aussage
    claim_type: ClaimType                 # Definition, Mechanism, etc.
    evidence_class: EvidenceClass         # A, B oder C
    freshness_required: bool = False
    recency_days: Optional[int] = None    # Falls Freshness wichtig
    required_source_classes: List[SourceClass] = field(default_factory=list)
    min_sources: int = 1                  # Wird aus EvidenceClass abgeleitet
    retrieval_ticket: Optional[RetrievalTicket] = None
    dependencies: List[str] = field(default_factory=list)  # Claim IDs von denen dieser abhängt
    status: ClaimStatus = ClaimStatus.PENDING
    section_id: str = ""                  # Welcher Outline-Abschnitt?
    
    def __post_init__(self):
        # Min_sources aus EvidenceClass ableiten
        if self.evidence_class == EvidenceClass.A:
            self.min_sources = 0
        elif self.evidence_class == EvidenceClass.B:
            self.min_sources = max(1, self.min_sources)
        elif self.evidence_class == EvidenceClass.C:
            self.min_sources = max(2, self.min_sources)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "evidence_class": self.evidence_class.value,
            "freshness_required": self.freshness_required,
            "recency_days": self.recency_days,
            "required_source_classes": [s.value for s in self.required_source_classes],
            "min_sources": self.min_sources,
            "retrieval_ticket": self.retrieval_ticket.to_dict() if self.retrieval_ticket else None,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "section_id": self.section_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Claim":
        ticket_data = data.get("retrieval_ticket")
        return cls(
            claim_id=data["claim_id"],
            claim_text=data["claim_text"],
            claim_type=ClaimType(data["claim_type"]),
            evidence_class=EvidenceClass(data["evidence_class"]),
            freshness_required=data.get("freshness_required", False),
            recency_days=data.get("recency_days"),
            required_source_classes=[SourceClass(s) for s in data.get("required_source_classes", [])],
            min_sources=data.get("min_sources", 1),
            retrieval_ticket=RetrievalTicket(**ticket_data) if ticket_data else None,
            dependencies=data.get("dependencies", []),
            status=ClaimStatus(data.get("status", "pending")),
            section_id=data.get("section_id", "")
        )


@dataclass
class ClaimRegister:
    """
    Das zentrale Register aller Claims.
    Enthält Qualitätsmetriken und Validierung.
    """
    question_brief: QuestionBrief
    term_map: TermMap
    outline: Outline
    claims: List[Claim]
    
    # Qualitätsmetriken
    min_total_claims: int = 12
    min_c_claims: int = 4
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_brief": self.question_brief.to_dict(),
            "term_map": self.term_map.to_dict(),
            "outline": self.outline.to_dict(),
            "claims": [c.to_dict() for c in self.claims]
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ClaimRegister":
        return cls(
            question_brief=QuestionBrief.from_dict(data["question_brief"]),
            term_map=TermMap.from_dict(data["term_map"]),
            outline=Outline.from_dict(data["outline"]),
            claims=[Claim.from_dict(c) for c in data.get("claims", [])]
        )
    
    # === Validierung ===
    
    def validate(self) -> Dict[str, Any]:
        """Prüft ob das ClaimRegister die Mindestanforderungen erfüllt."""
        issues = []
        
        total_claims = len(self.claims)
        c_claims = len([c for c in self.claims if c.evidence_class == EvidenceClass.C])
        b_claims = len([c for c in self.claims if c.evidence_class == EvidenceClass.B])
        
        if total_claims < self.min_total_claims:
            issues.append(f"Zu wenige Claims: {total_claims} < {self.min_total_claims}")
        
        if c_claims < self.min_c_claims:
            issues.append(f"Zu wenige C-Claims: {c_claims} < {self.min_c_claims}")
        
        # Prüfe ob B/C Claims Retrieval-Tickets haben
        for claim in self.claims:
            if claim.evidence_class in [EvidenceClass.B, EvidenceClass.C]:
                if not claim.retrieval_ticket or not claim.retrieval_ticket.queries:
                    issues.append(f"Claim {claim.claim_id} ({claim.evidence_class.value}) hat kein Retrieval-Ticket")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "stats": {
                "total_claims": total_claims,
                "a_claims": len([c for c in self.claims if c.evidence_class == EvidenceClass.A]),
                "b_claims": b_claims,
                "c_claims": c_claims
            }
        }
    
    # === Hilfsmethoden ===
    
    def get_claims_by_section(self, section_id: str) -> List[Claim]:
        return [c for c in self.claims if c.section_id == section_id]
    
    def get_claims_needing_evidence(self) -> List[Claim]:
        """Gibt alle B/C Claims zurück, die noch Evidenz brauchen."""
        return [
            c for c in self.claims 
            if c.evidence_class in [EvidenceClass.B, EvidenceClass.C]
            and c.status in [ClaimStatus.PENDING, ClaimStatus.INSUFFICIENT]
        ]
    
    def get_c_claims(self) -> List[Claim]:
        return [c for c in self.claims if c.evidence_class == EvidenceClass.C]


# =============================================================================
# PHASE 4-5: EVIDENCE & RATING
# =============================================================================

@dataclass
class SourceRating:
    """Bewertung einer Quelle nach 5 Dimensionen (0-3 pro Dimension)."""
    authority: int = 0       # Primärquelle / etabliert / unbekannt
    independence: int = 0    # Hersteller-nah? PR? Affiliate?
    recency: int = 0         # Passt zur Freshness-Anforderung?
    specificity: int = 0     # Belegt genau den Claim oder nur Kontext?
    consensus: int = 0       # Bestätigen mehrere Quellen dieselbe Aussage?
    
    @property
    def total(self) -> int:
        return self.authority + self.independence + self.recency + self.specificity + self.consensus
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "authority": self.authority,
            "independence": self.independence,
            "recency": self.recency,
            "specificity": self.specificity,
            "consensus": self.consensus,
            "total": self.total
        }


@dataclass
class Source:
    """Eine einzelne Quelle mit Bewertung."""
    source_id: str                    # z.B. "S-001"
    title: str
    publisher: str
    author: str = ""
    date: str = ""                    # YYYY-MM-DD
    url: str = ""
    source_class: SourceClass = SourceClass.SECONDARY
    extract: str = ""                 # Relevanter Auszug (paraphrasiert)
    supports_claims: List[str] = field(default_factory=list)  # Claim IDs
    rating: Optional[SourceRating] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "publisher": self.publisher,
            "author": self.author,
            "date": self.date,
            "url": self.url,
            "source_class": self.source_class.value,
            "extract": self.extract,
            "supports_claims": self.supports_claims,
            "rating": self.rating.to_dict() if self.rating else None
        }


@dataclass
class EvidencePack:
    """
    Evidenz-Paket für einen Claim.
    Enthält alle Quellen und deren Bewertung.
    """
    claim_id: str
    sources: List[Source] = field(default_factory=list)
    status: ClaimStatus = ClaimStatus.PENDING
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "sources": [s.to_dict() for s in self.sources],
            "status": self.status.value,
            "notes": self.notes
        }
    
    def is_fulfilled(self, min_sources: int, min_score: int = 10) -> bool:
        """Prüft ob die Evidenzanforderungen erfüllt sind."""
        if len(self.sources) < min_sources:
            return False
        
        # Prüfe ob genug Quellen den Mindest-Score haben
        good_sources = [s for s in self.sources if s.rating and s.rating.total >= min_score]
        return len(good_sources) >= min_sources
    
    def get_independence_score(self) -> float:
        """Berechnet den Anteil unabhängiger Quellen."""
        if not self.sources:
            return 0.0
        
        publishers = set()
        for source in self.sources:
            publishers.add(source.publisher.lower())
        
        # Mehr verschiedene Publisher = höhere Unabhängigkeit
        return len(publishers) / len(self.sources)


# =============================================================================
# PHASE 7: REVIEW
# =============================================================================

@dataclass
class ReviewIssue:
    """Ein einzelnes Problem im Review."""
    issue_type: str        # "uncovered_claim", "hallucination", "contradiction", "style"
    severity: str          # "critical", "major", "minor"
    description: str
    claim_id: Optional[str] = None
    location: str = ""     # Wo im Text?
    suggested_action: str = ""


@dataclass
class ReviewReport:
    """
    Ergebnis der Editorial Review.
    Prüft Claim Coverage und Evidenzqualität.
    """
    # Coverage Metriken
    total_claims: int = 0
    claims_in_text: int = 0
    c_claims_with_evidence: int = 0
    c_claims_total: int = 0
    
    # Issues
    issues: List[ReviewIssue] = field(default_factory=list)
    
    # Neue Claims (Hallucination Surface)
    unanchored_statements: List[str] = field(default_factory=list)
    
    # Contradictions
    contradictions: List[Dict[str, str]] = field(default_factory=list)
    
    # Verdict
    passed: bool = False
    needs_gap_loop: bool = False
    gap_claims: List[str] = field(default_factory=list)  # Claims die mehr Evidenz brauchen
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage": {
                "total_claims": self.total_claims,
                "claims_in_text": self.claims_in_text,
                "c_claims_with_evidence": self.c_claims_with_evidence,
                "c_claims_total": self.c_claims_total,
                "claim_coverage_rate": self.claims_in_text / self.total_claims if self.total_claims > 0 else 0,
                "c_claim_evidence_rate": self.c_claims_with_evidence / self.c_claims_total if self.c_claims_total > 0 else 0
            },
            "issues": [
                {
                    "type": i.issue_type,
                    "severity": i.severity,
                    "description": i.description,
                    "claim_id": i.claim_id,
                    "location": i.location,
                    "suggested_action": i.suggested_action
                }
                for i in self.issues
            ],
            "hallucination_surface": len(self.unanchored_statements),
            "unanchored_statements": self.unanchored_statements,
            "contradictions": self.contradictions,
            "verdict": {
                "passed": self.passed,
                "needs_gap_loop": self.needs_gap_loop,
                "gap_claims": self.gap_claims
            }
        }
    
    @property
    def claim_coverage_rate(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return self.claims_in_text / self.total_claims
    
    @property
    def c_claim_evidence_rate(self) -> float:
        if self.c_claims_total == 0:
            return 1.0  # Keine C-Claims = 100% erfüllt
        return self.c_claims_with_evidence / self.c_claims_total
    
    @property
    def hallucination_count(self) -> int:
        return len(self.unanchored_statements)
