from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DocumentItem(BaseModel):
    filename: str
    format: str
    description: Optional[str] = None
    page_count: Optional[int] = None
    record_count: Optional[int] = None

class Clarification(BaseModel):
    question: str
    answer: str

class Requirements(BaseModel):
    agent_name: str
    purpose: str
    target_audience: str
    scope: str
    tone: str
    must_answer_topics: List[str]
    must_refuse_topics: List[str]
    required_tools: List[str]
    document_inventory: List[DocumentItem]
    assumptions: List[str]
    ambiguities: List[str]
    unsupported_requirements: List[str]
    clarifications: List[Clarification] = Field(default_factory=list)
