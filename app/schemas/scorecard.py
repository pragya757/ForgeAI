from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CaseEvaluationResult(BaseModel):
    test_id: str
    question: str
    passed: bool
    outcome_classification: str = "correct_with_evidence"  # "correct_with_evidence", "correct_without_evidence", "partially_correct", "incorrect", "correct_refusal", "incorrect_refusal"
    grounding_score: float = Field(ge=0.0, le=1.0)
    factual_correctness: float = Field(ge=0.0, le=1.0)
    citation_correctness: float = Field(ge=0.0, le=1.0)
    refusal_correctness: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    output_contract_compliance: float = Field(ge=0.0, le=1.0)
    verdict_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    uncertainty_flag: bool = False
    evidence_reasoning: Optional[str] = None
    failure_reasons: List[str] = Field(default_factory=list)
    agent_response: str
    retrieved_sources: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: Optional[str] = None

class IterationScorecard(BaseModel):
    iteration: int
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float = Field(ge=0.0, le=1.0)
    metric_breakdown: Dict[str, float] = Field(default_factory=dict)
    failure_distribution: Dict[str, int] = Field(default_factory=dict)
    outcome_distribution: Dict[str, int] = Field(default_factory=dict)
    status: str  # "PASS", "FAIL", "NEEDS_OPTIMIZATION"
    case_results: List[CaseEvaluationResult] = Field(default_factory=list)

class IterationLog(BaseModel):
    iteration_number: int
    previous_score: float
    failed_test_ids: List[str]
    failure_categories: List[str]
    identified_root_causes: str
    changes_applied: List[Dict[str, Any]]
    reason_for_each_change: str
    updated_configuration: Dict[str, Any]
    new_score: float
    improvement_or_regression: str
