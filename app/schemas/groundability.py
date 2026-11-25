from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EvidenceReference(BaseModel):
    source_document: str
    page_or_record: Optional[str] = None
    excerpt: str
    relevance_score: float = Field(default=0.9, ge=0.0, le=1.0)

class SupportedTopic(BaseModel):
    topic: str
    evidence_sources: List[str]
    coverage_summary: str
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)

class PartiallySupportedTopic(BaseModel):
    topic: str
    evidence_sources: List[str]
    missing_aspects: str
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)

class UnsupportedTopic(BaseModel):
    topic: str
    reason: str
    absence_nature: str = "missing_from_corpus"  # "missing_from_corpus", "inherently_nonexistent", "unsupported_capability"
    confidence_score: float = Field(default=0.95, ge=0.0, le=1.0)

class GroundabilityReport(BaseModel):
    supported_topics: List[SupportedTopic]
    partially_supported_topics: List[PartiallySupportedTopic] = Field(default_factory=list)
    unsupported_topics: List[UnsupportedTopic] = Field(default_factory=list)
    document_coverage_map: Dict[str, List[str]] = Field(default_factory=dict)
    refusal_recommendations: List[str] = Field(default_factory=list)
    sanitized_answerable_topics: List[str] = Field(default_factory=list)
    overall_groundability_score: float = Field(ge=0.0, le=1.0)
