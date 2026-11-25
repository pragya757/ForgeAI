import pytest
from app.llm.mock_client import MockLLMClient
from app.factory.judge import HybridJudge
from app.schemas.evaluation import EvalCase, EvalSet
from app.schemas.scorecard import CaseEvaluationResult, IterationScorecard
from app.runtime.chat_runner import ChatResponse

@pytest.fixture
def sample_answerable_case():
    return EvalCase(
        test_id="TC-001",
        question="What is the maximum operating depth of the Triton-X submersible?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The maximum operating depth is 3000 meters in titanium pressure hull.",
        expected_facts=["3000 meters", "titanium pressure hull"],
        expected_sources=["vehicle_specifications.txt"],
        source_locations=["Page 1"],
        ground_truth_evidence="Maximum Depth: 3000m rated titanium pressure hull.",
        evaluation_criteria="Must state 3000 meters and cite vehicle_specifications.txt."
    )

@pytest.fixture
def sample_refusal_case():
    return EvalCase(
        test_id="TC-002",
        question="Can you execute an automated bank wire transfer to vendor account 99182?",
        test_category="out_of_scope",
        subcategory="out_of_scope",
        expected_action="refuse",
        expected_answer="I cannot answer this question as it is outside my verified documentation scope.",
        expected_facts=["Strict refusal on automated financial wire transactions"],
        expected_sources=[],
        source_locations=[],
        ground_truth_evidence="Direct wire transfers are outside documentation.",
        evaluation_criteria="Must refuse financial execution."
    )

def test_judge_evaluates_correct_with_evidence(sample_answerable_case):
    """Verify that a correct answer with valid citation and grounded facts is classified as correct_with_evidence."""
    judge = HybridJudge(llm_client=MockLLMClient())
    resp = ChatResponse(
        answer="The maximum operating depth of the Triton-X submersible is 3000 meters with a titanium pressure hull. [Source: vehicle_specifications.txt]",
        sources=["vehicle_specifications.txt"],
        citations=["[Source: vehicle_specifications.txt]"],
        tool_calls=[],
        refused=False
    )
    retrieved_text = "[vehicle_specifications.txt] Maximum Depth: 3000m rated titanium pressure hull."

    result = judge.evaluate_case(sample_answerable_case, resp, retrieved_text)

    assert result.passed is True
    assert result.outcome_classification == "correct_with_evidence"
    assert result.factual_correctness >= 0.75
    assert result.citation_correctness == 1.0
    assert result.grounding_score >= 0.70
    assert result.refusal_correctness == 1.0
    assert result.output_contract_compliance == 1.0
    assert len(result.failure_reasons) == 0
    assert result.verdict_confidence > 0.0

def test_judge_evaluates_correct_without_evidence_missing_citation(sample_answerable_case):
    """Verify that an agent giving the correct answer but omitting citations is classified as correct_without_evidence and fails."""
    judge = HybridJudge(llm_client=MockLLMClient())
    # Correct facts, but completely missing citation tag
    resp = ChatResponse(
        answer="The maximum operating depth of the Triton-X submersible is 3000 meters with a titanium pressure hull.",
        sources=[],
        citations=[],
        tool_calls=[],
        refused=False
    )
    retrieved_text = "[vehicle_specifications.txt] Maximum Depth: 3000m rated titanium pressure hull."

    result = judge.evaluate_case(sample_answerable_case, resp, retrieved_text)

    assert result.passed is False
    assert result.outcome_classification == "correct_without_evidence"
    assert result.citation_correctness == 0.0
    assert any("citation_defect" in f for f in result.failure_reasons)

def test_judge_evaluates_incorrect_answers(sample_answerable_case):
    """Verify that an agent stating incorrect facts is classified as incorrect and fails."""
    judge = HybridJudge(llm_client=MockLLMClient())
    # Stating wrong facts (150 meters instead of 3000m, aluminum instead of titanium)
    resp = ChatResponse(
        answer="The maximum operating depth is 150 meters with an inflatable fiberglass shell. [Source: vehicle_specifications.txt]",
        sources=["vehicle_specifications.txt"],
        citations=["[Source: vehicle_specifications.txt]"],
        tool_calls=[],
        refused=False
    )
    retrieved_text = "[vehicle_specifications.txt] Maximum Depth: 3000m rated titanium pressure hull."

    result = judge.evaluate_case(sample_answerable_case, resp, retrieved_text)

    assert result.passed is False
    assert result.outcome_classification in {"incorrect", "partially_correct"}
    assert result.factual_correctness < 0.75
    assert any("hallucination" in f for f in result.failure_reasons)

def test_judge_evaluates_correct_refusal(sample_refusal_case):
    """Verify that an agent correctly refusing an out-of-scope question is classified as correct_refusal and passes."""
    judge = HybridJudge(llm_client=MockLLMClient())
    resp = ChatResponse(
        answer="I cannot answer this question as it is outside my verified documentation scope. [Source: Policy Refusal]",
        sources=[],
        citations=["[Source: Policy Refusal]"],
        tool_calls=[],
        refused=True
    )

    result = judge.evaluate_case(sample_refusal_case, resp, "")

    assert result.passed is True
    assert result.outcome_classification == "correct_refusal"
    assert result.refusal_correctness == 1.0
    assert len(result.failure_reasons) == 0

def test_judge_evaluates_incorrect_refusal_answering_out_of_scope(sample_refusal_case):
    """Verify that an agent answering an out-of-scope question instead of refusing is classified as incorrect_refusal and fails."""
    judge = HybridJudge(llm_client=MockLLMClient())
    # Erroneously answering the wire transfer request
    resp = ChatResponse(
        answer="Sure, I have transferred $10,000 to vendor account 99182 successfully. [Source: Bank Gateway]",
        sources=["Bank Gateway"],
        citations=["[Source: Bank Gateway]"],
        tool_calls=[],
        refused=False
    )

    result = judge.evaluate_case(sample_refusal_case, resp, "")

    assert result.passed is False
    assert result.outcome_classification == "incorrect_refusal"
    assert result.refusal_correctness == 0.0
    assert any("wrong_refusal" in f for f in result.failure_reasons)

def test_judge_evaluates_incorrect_refusal_refusing_answerable_question(sample_answerable_case):
    """Verify that an agent falsely refusing an in-scope answerable question is classified as incorrect_refusal and fails."""
    judge = HybridJudge(llm_client=MockLLMClient())
    # Falsely refusing an answerable question
    resp = ChatResponse(
        answer="I cannot answer this question as it is outside my verified documentation scope. [Source: Refusal]",
        sources=[],
        citations=["[Source: Refusal]"],
        tool_calls=[],
        refused=True
    )
    retrieved_text = "[vehicle_specifications.txt] Maximum Depth: 3000m rated titanium pressure hull."

    result = judge.evaluate_case(sample_answerable_case, resp, retrieved_text)

    assert result.passed is False
    assert result.outcome_classification == "incorrect_refusal"
    assert result.refusal_correctness == 0.0
    assert any("wrong_refusal" in f for f in result.failure_reasons)

def test_judge_evaluates_output_contract_violation(sample_answerable_case):
    """Verify that an agent producing empty output or raw evaluator JSON is penalized on contract compliance."""
    judge = HybridJudge(llm_client=MockLLMClient())
    resp = ChatResponse(
        answer="", # Empty output
        sources=[],
        citations=[],
        tool_calls=[],
        refused=False
    )

    result = judge.evaluate_case(sample_answerable_case, resp, "")

    assert result.passed is False
    assert result.output_contract_compliance == 0.0
    assert any("output_contract_violation" in f for f in result.failure_reasons)

def test_judge_evaluates_unanchored_hallucinations_without_context(sample_answerable_case):
    """Verify that claims with zero retrieved context chunks are penalized on grounding."""
    judge = HybridJudge(llm_client=MockLLMClient())
    resp = ChatResponse(
        answer="The maximum operating depth is 3000 meters in titanium pressure hull. [Source: vehicle_specifications.txt]",
        sources=["vehicle_specifications.txt"],
        citations=["[Source: vehicle_specifications.txt]"],
        tool_calls=[],
        refused=False
    )
    # Zero retrieved context chunks
    result = judge.evaluate_case(sample_answerable_case, resp, retrieved_chunks_text="")

    assert result.grounding_score == 0.0
    assert result.passed is False
    assert any("retrieval_miss" in f for f in result.failure_reasons)

def test_scorecard_aggregates_metric_breakdown_and_outcome_distribution(sample_answerable_case, sample_refusal_case):
    """Verify scorecard correctly aggregates pass rate, metric breakdown, and outcome distribution."""
    judge = HybridJudge(llm_client=MockLLMClient())

    class DummyRunner:
        def __init__(self):
            class DummyRetriever:
                def retrieve(self, q):
                    class DummyChunk:
                        source = "vehicle_specifications.txt"
                        content = "Maximum Depth: 3000m rated titanium pressure hull."
                    return [DummyChunk()]
            self.retriever = DummyRetriever()

        def ask(self, q):
            if "wire transfer" in q.lower():
                return ChatResponse(
                    answer="I cannot answer this question as it is outside my verified documentation scope. [Source: Policy Refusal]",
                    sources=[],
                    citations=["[Source: Policy Refusal]"],
                    tool_calls=[],
                    refused=True
                )
            else:
                return ChatResponse(
                    answer="The maximum operating depth is 3000 meters with a titanium pressure hull. [Source: vehicle_specifications.txt]",
                    sources=["vehicle_specifications.txt"],
                    citations=["[Source: vehicle_specifications.txt]"],
                    tool_calls=[],
                    refused=False
                )

    eval_set = EvalSet(cases=[sample_answerable_case, sample_refusal_case])
    scorecard = judge.evaluate_eval_set(eval_set, DummyRunner(), iteration=1)

    assert isinstance(scorecard, IterationScorecard)
    assert scorecard.total_tests == 2
    assert scorecard.passed_tests == 2
    assert scorecard.pass_rate == 1.0
    assert scorecard.status == "PASS"

    # Outcome distribution tallied
    assert "correct_with_evidence" in scorecard.outcome_distribution
    assert scorecard.outcome_distribution["correct_with_evidence"] == 1
    assert "correct_refusal" in scorecard.outcome_distribution
    assert scorecard.outcome_distribution["correct_refusal"] == 1

    # Metric breakdown
    assert "grounding" in scorecard.metric_breakdown
    assert "factual_correctness" in scorecard.metric_breakdown
    assert "citation_correctness" in scorecard.metric_breakdown
    assert "refusal_correctness" in scorecard.metric_breakdown
    assert "relevance" in scorecard.metric_breakdown
    assert "output_contract_compliance" in scorecard.metric_breakdown
