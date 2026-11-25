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
    score_difference: float = 0.0
    resolved_test_ids: List[str] = Field(default_factory=list)
    regressed_test_ids: List[str] = Field(default_factory=list)
    regression_detected: bool = False
    change_accepted: bool = True
    snapshot_path: Optional[str] = None

class MetricComparison(BaseModel):
    metric_name: str
    initial_value: float = Field(ge=0.0, le=1.0)
    final_value: float = Field(ge=0.0, le=1.0)
    delta: float
    improvement_status: str  # "IMPROVED", "REGRESSED", "UNCHANGED"

class FailedCaseAudit(BaseModel):
    test_id: str
    question: str
    category: str = "direct_factual"
    expected_action: str = "answer"
    expected_answer: Optional[str] = None
    raw_agent_response: str
    failure_reasons: List[str] = Field(default_factory=list)
    outcome_classification: str = "incorrect"
    judge_evidence_reasoning: Optional[str] = None
    grounding_score: float
    factual_correctness: float
    citation_correctness: float
    refusal_correctness: float
    relevance_score: float = 1.0
    output_contract_compliance: float
    retrieved_sources: List[str] = Field(default_factory=list)

class QualityReportData(BaseModel):
    generated_at: str
    agent_name: str
    final_status: str
    user_brief: str
    document_inventory: List[Dict[str, Any]] = Field(default_factory=list)
    structured_requirements: Dict[str, Any] = Field(default_factory=dict)
    groundability_analysis: Dict[str, Any] = Field(default_factory=dict)
    agent_configuration: Dict[str, Any] = Field(default_factory=dict)
    selected_tools_and_justifications: Dict[str, Any] = Field(default_factory=dict)
    evaluation_dataset_summary: Dict[str, Any] = Field(default_factory=dict)
    initial_scorecard: Dict[str, Any] = Field(default_factory=dict)
    optimization_iterations: List[Dict[str, Any]] = Field(default_factory=list)
    before_and_after_comparison: Dict[str, MetricComparison] = Field(default_factory=dict)
    remaining_failed_cases: List[FailedCaseAudit] = Field(default_factory=list)
    unsupported_topics: List[Dict[str, Any]] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)
    reproducible_metrics: Dict[str, float] = Field(default_factory=dict)
