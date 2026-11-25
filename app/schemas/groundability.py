from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SupportedTopic(BaseModel):
    topic: str
    evidence_sources: List[str]
    coverage_summary: str

class PartiallySupportedTopic(BaseModel):
    topic: str
    evidence_sources: List[str]
    missing_aspects: str

class UnsupportedTopic(BaseModel):
    topic: str
    reason: str

class GroundabilityReport(BaseModel):
    supported_topics: List[SupportedTopic]
    partially_supported_topics: List[PartiallySupportedTopic] = Field(default_factory=list)
    unsupported_topics: List[UnsupportedTopic] = Field(default_factory=list)
    document_coverage_map: Dict[str, List[str]] = Field(default_factory=dict)
    refusal_recommendations: List[str] = Field(default_factory=list)
    overall_groundability_score: float = Field(ge=0.0, le=1.0)
