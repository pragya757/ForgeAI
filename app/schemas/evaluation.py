from typing import List, Optional
from pydantic import BaseModel, Field

class EvalCase(BaseModel):
    test_id: str
    question: str
    test_category: str  # "answerable", "out_of_scope", "edge_case"
    subcategory: Optional[str] = None  # "direct_factual", "multi_hop", "cross_document", "ambiguous", "missing_information", "out_of_scope", "contradictory_document", "misleading_assumption"
    expected_action: str  # "answer", "refuse", "clarify"
    expected_answer: str
    expected_facts: List[str] = Field(default_factory=list)
    expected_sources: List[str] = Field(default_factory=list)
    source_locations: List[str] = Field(default_factory=list)
    ground_truth_evidence: str
    evaluation_criteria: str

class EvalSet(BaseModel):
    cases: List[EvalCase] = Field(default_factory=list)
