"""
HayMAS Evidence-Gated Research & Writing System

Ein claim-getriebenes System für hochwertige, zitierfähige Wissensartikel.
Basiert auf dem Evidence-Gated Design Dokument.
"""

from .models import (
    QuestionBrief,
    TermMap,
    Claim,
    ClaimType,
    EvidenceClass,
    RetrievalTicket,
    ClaimRegister,
    Source,
    SourceRating,
    EvidencePack,
    ReviewReport,
    Outline,
    OutlineSection
)

from .agents import (
    QueryNormalizerAgent,
    ClaimMinerAgent,
    EvidencePlannerAgent,
    TargetedRetrieverAgent,
    EvidenceRaterAgent,
    ClaimBoundedWriterAgent,
    EditorialReviewerAgent,
    FinalVerifierAgent
)

from .orchestrator import EvidenceGatedOrchestrator

__all__ = [
    # Models
    "QuestionBrief",
    "TermMap", 
    "Claim",
    "ClaimType",
    "EvidenceClass",
    "RetrievalTicket",
    "ClaimRegister",
    "Source",
    "SourceRating",
    "EvidencePack",
    "ReviewReport",
    "Outline",
    "OutlineSection",
    # Agents
    "QueryNormalizerAgent",
    "ClaimMinerAgent",
    "EvidencePlannerAgent",
    "TargetedRetrieverAgent",
    "EvidenceRaterAgent",
    "ClaimBoundedWriterAgent",
    "EditorialReviewerAgent",
    "FinalVerifierAgent",
    # Orchestrator
    "EvidenceGatedOrchestrator"
]
