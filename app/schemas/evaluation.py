from typing import List, Optional
from pydantic import BaseModel, Field

class EvalCase(BaseModel):
    test_id: str
    question: str
    test_category: str  # "answerable", "out_of_scope", "edge_case"
    expected_answer: str
    expected_sources: List[str] = Field(default_factory=list)
    expected_action: str  # "answer", "refuse", "clarify"
    ground_truth_evidence: str
    evaluation_criteria: str

class EvalSet(BaseModel):
    cases: List[EvalCase] = Field(default_factory=list)
