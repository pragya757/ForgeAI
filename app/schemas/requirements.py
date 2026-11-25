from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DocumentItem(BaseModel):
    filename: str
    format: str
    description: Optional[str] = None
    page_count: Optional[int] = None
    record_count: Optional[int] = None
    content_summary: Optional[str] = None
    detected_topics: List[str] = Field(default_factory=list)

class Clarification(BaseModel):
    question: str
    answer: str

class InformationContradiction(BaseModel):
    topic: str
    conflicting_statements: List[str] = Field(default_factory=list)
    conflicting_sources: List[str] = Field(default_factory=list)
    resolution_strategy: str = "Decline to answer contradictory statements without human confirmation."

class InformationGapAnalysis(BaseModel):
    missing_information: List[str] = Field(default_factory=list)
    contradictory_information: List[InformationContradiction] = Field(default_factory=list)
    duplicated_information: List[str] = Field(default_factory=list)
    incomplete_information: List[str] = Field(default_factory=list)

class Requirements(BaseModel):
    agent_name: str
    purpose: str
    user_intent: str = "Informational query answering from verified corpus"
    target_audience: str
    domain: str = "General Enterprise"
    scope: str
    tone: str
    constraints: List[str] = Field(default_factory=list)
    must_answer_topics: List[str]
    must_refuse_topics: List[str]
    required_tools: List[str]
    document_inventory: List[DocumentItem]
    information_gaps: InformationGapAnalysis = Field(default_factory=InformationGapAnalysis)
    assumptions: List[str]
    ambiguities: List[str]
    unsupported_requirements: List[str]
    clarifications: List[Clarification] = Field(default_factory=list)
