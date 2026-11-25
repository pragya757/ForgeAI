import os
import json
import pytest
from typing import List
from unittest.mock import patch, MagicMock

from app.llm.mock_client import MockLLMClient
from app.factory.critic_optimizer import CriticOptimizer, FailureDiagnosis
from app.schemas.agent_definition import AgentDefinition, OutputContract, CitationRequirements, ModelConfig
from app.schemas.scorecard import CaseEvaluationResult, IterationScorecard, IterationLog
from app.schemas.evaluation import EvalSet, EvalCase

@pytest.fixture
def base_agent():
    return AgentDefinition(
        agent_name="Fleet Procurement Assistant",
        description="Assists with maritime vessel spare parts procurement.",
        system_prompt="Answer procurement inquiries strictly from technical manuals.",
        target_audience="Procurement Officers & Marine Engineers",
        supported_topics=["Spare parts pricing", "Lead times", "Part numbers"],
        unsupported_topics=["Employee salaries", "Wire transfers"],
        must_refuse_topics=["Employee salaries", "Wire transfers"],
        document_references=["spare_parts_catalog.csv"],
        chunk_size=400,
        chunk_overlap=80,
        top_k=3,
        similarity_threshold=0.40,
        output_contract=OutputContract(format="markdown"),
        citation_requirements=CitationRequirements(mandatory=True, tag_format="[Source: <filename>]"),
        refusal_policy="Strict",
        model_config=ModelConfig()
    )

@pytest.fixture
def mock_eval_set():
    cases = [
        EvalCase(
            test_id=f"TEST-{i:03d}",
            question=f"Question {i} regarding spare parts?",
            test_category="answerable",
            subcategory="direct_factual",
            expected_action="answer",
            expected_answer="Part NV-PUMP-001 price is $4,250.00.",
            expected_facts=["Fact A"],
            expected_sources=["spare_parts_catalog.csv"],
            source_locations=["line 10"],
            ground_truth_evidence="Fact A excerpt",
            evaluation_criteria="State Fact A clearly."
        ) for i in range(1, 6)
    ]
    return EvalSet(cases=cases)

# 1. Test Iteration Limit Strict Ceiling
def test_iteration_limit_strictly_capped_at_three():
    # Attempt to set max_iterations to 10
    critic_10 = CriticOptimizer(max_iterations=10)
    assert critic_10.max_iterations == 3, "CriticOptimizer must clamp max_iterations to 3"

    # Attempt to set max_iterations to 5
    critic_5 = CriticOptimizer(max_iterations=5)
    assert critic_5.max_iterations == 3, "CriticOptimizer must clamp max_iterations to 3"

    # Attempt to set max_iterations to 0 or negative
    critic_0 = CriticOptimizer(max_iterations=0)
    assert critic_0.max_iterations == 1, "CriticOptimizer must enforce at least 1 iteration"

    critic_neg = CriticOptimizer(max_iterations=-5)
    assert critic_neg.max_iterations == 1, "CriticOptimizer must enforce at least 1 iteration"

def test_iteration_loop_cannot_exceed_three_iterations(tmp_path, base_agent, mock_eval_set):
    """Even if evaluations keep failing and max_iterations=10 is requested, loop stops strictly at 3."""
    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=10)
    assert critic.max_iterations == 3

    # Mock HybridJudge.evaluate_eval_set to return failing results with changing failure profiles
    call_count = 0
    def mock_eval(eval_set, runner, iteration):
        nonlocal call_count
        call_count += 1
        # Iteration 1: 20% pass (TEST-001 pass, 002-005 fail)
        # Iteration 2: 40% pass (TEST-001,002 pass, 003-005 fail)
        # Iteration 3: 60% pass (TEST-001..003 pass, 004-005 fail)
        # Never reaches 0.90 target pass rate
        passed_count = iteration
        return IterationScorecard(
            iteration=iteration,
            total_tests=5,
            passed_tests=passed_count,
            failed_tests=5 - passed_count,
            pass_rate=round(passed_count / 5.0, 2),
            status="FAIL",
            case_results=[
                CaseEvaluationResult(
                    test_id=f"TEST-00{i}",
                    question=f"Q{i}",
                    passed=(i <= passed_count),
                    grounding_score=1.0 if i <= passed_count else 0.2,
                    factual_correctness=1.0 if i <= passed_count else 0.2,
                    citation_correctness=1.0 if i <= passed_count else 0.2,
                    refusal_correctness=1.0,
                    relevance_score=1.0 if i <= passed_count else 0.5,
                    output_contract_compliance=1.0,
                    failure_reasons=["retrieval_miss: missing chunks"] if i > passed_count else [],
                    agent_response="resp"
                ) for i in range(1, 6)
            ]
        )

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set", side_effect=mock_eval):
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(tmp_path / "artifacts"),
            target_pass_rate=0.90
        )

    # Strictly at most 3 iterations were run
    assert len(scorecards) == 3, f"Expected exactly 3 scorecards, got {len(scorecards)}"
    assert call_count == 3, f"Expected exactly 3 evaluations, got {call_count}"
    assert len(logs) == 2, f"Expected 2 optimization logs (between iter 1->2 and 2->3), got {len(logs)}"

# 2. Test Configuration Snapshots Saved Per Iteration
def test_configuration_snapshots_saved_per_iteration(tmp_path, base_agent, mock_eval_set):
    artifacts_dir = tmp_path / "snapshots_test"
    artifacts_dir.mkdir()

    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=3)

    iter_counter = 0
    def mock_eval_progress(eval_set, runner, iteration):
        nonlocal iter_counter
        iter_counter += 1
        # Iteration 1: 50% pass, Iteration 2: 70% pass, Iteration 3: 95% pass
        pass_rate = 0.50 if iteration == 1 else (0.70 if iteration == 2 else 0.95)
        passed_count = int(pass_rate * 5)
        return IterationScorecard(
            iteration=iteration,
            total_tests=5,
            passed_tests=passed_count,
            failed_tests=5 - passed_count,
            pass_rate=pass_rate,
            status="PASS" if pass_rate >= 0.90 else "FAIL",
            case_results=[
                CaseEvaluationResult(
                    test_id=f"TEST-00{i}",
                    question=f"Q{i}",
                    passed=(i <= passed_count),
                    grounding_score=1.0 if i <= passed_count else 0.3,
                    factual_correctness=1.0 if i <= passed_count else 0.3,
                    citation_correctness=1.0 if i <= passed_count else 0.3,
                    refusal_correctness=1.0,
                    relevance_score=1.0 if i <= passed_count else 0.5,
                    output_contract_compliance=1.0,
                    failure_reasons=["citation_defect: missing tag"] if i > passed_count else [],
                    agent_response="resp"
                ) for i in range(1, 6)
            ]
        )

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set", side_effect=mock_eval_progress):
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(artifacts_dir),
            target_pass_rate=0.90
        )

    # Check snapshots
    assert (artifacts_dir / "agent_definition_initial.json").exists()
    assert (artifacts_dir / "agent_definition_iter_1.json").exists()
    assert (artifacts_dir / "agent_definition_iter_2.json").exists()
    assert (artifacts_dir / "agent_definition_iter_3.json").exists()
    assert (artifacts_dir / "agent_definition_final.json").exists()
    assert (artifacts_dir / "iteration_logs.json").exists()
    assert (artifacts_dir / "scorecards.json").exists()

    # Verify initial snapshot matches original base_agent
    with open(artifacts_dir / "agent_definition_initial.json") as f:
        data = json.load(f)
        assert data["agent_name"] == base_agent.agent_name
        assert data["top_k"] == base_agent.top_k

# 3. Test Original Configuration Preserved and Untargeted Fields Untouched
def test_original_configuration_preserved_and_unrelated_fields_untouched(tmp_path, base_agent, mock_eval_set):
    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=2)

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set") as mock_judge:
        mock_judge.return_value = IterationScorecard(
            iteration=1,
            total_tests=5,
            passed_tests=5,
            failed_tests=0,
            pass_rate=1.0,
            status="PASS",
            case_results=[]
        )
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(tmp_path / "artifacts"),
            target_pass_rate=0.90
        )

    assert critic.original_agent is not None
    assert critic.original_agent.agent_name == base_agent.agent_name
    assert critic.original_agent.supported_topics == base_agent.supported_topics
    assert critic.original_agent.unsupported_topics == base_agent.unsupported_topics
    assert critic.original_agent.target_audience == base_agent.target_audience

# 4. Test Regression Detection and Rollback Safeguard
def test_regression_detection_and_rollback(tmp_path, base_agent, mock_eval_set):
    """
    If iteration 2 causes a regression on previously passing tests and net score drops,
    the optimizer must detect regression, reject the change, rollback to previous accepted snapshot.
    """
    artifacts_dir = tmp_path / "rollback_test"
    artifacts_dir.mkdir()

    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=3)

    iter_count = 0
    def mock_eval_regression(eval_set, runner, iteration):
        nonlocal iter_count
        iter_count += 1
        if iteration == 1:
            # Iteration 1: TEST-001, TEST-002 PASS (40% pass)
            return IterationScorecard(
                iteration=1,
                total_tests=5,
                passed_tests=2,
                failed_tests=3,
                pass_rate=0.40,
                status="FAIL",
                case_results=[
                    CaseEvaluationResult(
                        test_id="TEST-001", question="Q1", passed=True,
                        grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
                        refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-002", question="Q2", passed=True,
                        grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
                        refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-003", question="Q3", passed=False,
                        grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                        refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: not retrieved"],
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-004", question="Q4", passed=False,
                        grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                        refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: not retrieved"],
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-005", question="Q5", passed=False,
                        grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                        refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: not retrieved"],
                        agent_response="resp"
                    )
                ]
            )
        else:
            # Iteration 2: REGRESSION! TEST-001 broke! Only TEST-002 passes (20% pass)
            return IterationScorecard(
                iteration=2,
                total_tests=5,
                passed_tests=1,
                failed_tests=4,
                pass_rate=0.20,
                status="FAIL",
                case_results=[
                    CaseEvaluationResult(
                        test_id="TEST-001", question="Q1", passed=False,  # Regressed!
                        grounding_score=0.0, factual_correctness=0.0, citation_correctness=0.0,
                        refusal_correctness=1.0, relevance_score=0.0, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: broke due to threshold"],
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-002", question="Q2", passed=True,
                        grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
                        refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-003", question="Q3", passed=False,
                        grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                        refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: not retrieved"],
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-004", question="Q4", passed=False,
                        grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                        refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: not retrieved"],
                        agent_response="resp"
                    ),
                    CaseEvaluationResult(
                        test_id="TEST-005", question="Q5", passed=False,
                        grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                        refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                        failure_reasons=["retrieval_miss: not retrieved"],
                        agent_response="resp"
                    )
                ]
            )

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set", side_effect=mock_eval_regression):
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(artifacts_dir),
            target_pass_rate=0.90
        )

    assert len(logs) >= 1
    revert_log = logs[0]
    assert revert_log.regression_detected is True, "Must flag regression_detected as True"
    assert revert_log.change_accepted is False, "Must reject the regressing change"
    assert "TEST-001" in revert_log.regressed_test_ids
    assert "REVERTED" in revert_log.improvement_or_regression

    # The final agent was rolled back to the accepted iteration 1 config (top_k=3, similarity_threshold=0.40)
    assert final_agent.top_k == base_agent.top_k
    assert final_agent.similarity_threshold == base_agent.similarity_threshold

# 5. Test Early Stopping on Target Pass Rate
def test_early_stopping_on_target_pass_rate(tmp_path, base_agent, mock_eval_set):
    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=3)

    call_count = 0
    def mock_eval_high(eval_set, runner, iteration):
        nonlocal call_count
        call_count += 1
        return IterationScorecard(
            iteration=iteration,
            total_tests=5,
            passed_tests=5,
            failed_tests=0,
            pass_rate=1.0,
            status="PASS",
            case_results=[]
        )

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set", side_effect=mock_eval_high):
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(tmp_path / "artifacts"),
            target_pass_rate=0.90
        )

    assert call_count == 1, "Must terminate on first iteration when target pass rate is met"
    assert len(scorecards) == 1
    assert len(logs) == 0  # No optimization needed

# 6. Test Early Stopping on Stagnation
def test_early_stopping_on_stagnation(tmp_path, base_agent, mock_eval_set):
    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=3)

    call_count = 0
    def mock_eval_stagnant(eval_set, runner, iteration):
        nonlocal call_count
        call_count += 1
        # Exactly identical failure set and pass rate on iteration 1 and 2
        return IterationScorecard(
            iteration=iteration,
            total_tests=5,
            passed_tests=3,
            failed_tests=2,
            pass_rate=0.60,
            status="FAIL",
            case_results=[
                CaseEvaluationResult(
                    test_id="TEST-001", question="Q1", passed=True,
                    grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
                    refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
                    agent_response="resp"
                ),
                CaseEvaluationResult(
                    test_id="TEST-002", question="Q2", passed=True,
                    grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
                    refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
                    agent_response="resp"
                ),
                CaseEvaluationResult(
                    test_id="TEST-003", question="Q3", passed=True,
                    grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
                    refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
                    agent_response="resp"
                ),
                CaseEvaluationResult(
                    test_id="TEST-004", question="Q4", passed=False,
                    grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                    refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                    failure_reasons=["prompt_defect: unclear"],
                    agent_response="resp"
                ),
                CaseEvaluationResult(
                    test_id="TEST-005", question="Q5", passed=False,
                    grounding_score=0.2, factual_correctness=0.2, citation_correctness=0.2,
                    refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
                    failure_reasons=["prompt_defect: unclear"],
                    agent_response="resp"
                ),
            ]
        )

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set", side_effect=mock_eval_stagnant):
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(tmp_path / "artifacts"),
            target_pass_rate=0.90
        )

    # Iteration 1 runs, logs change, iteration 2 runs, detects stagnation (identical failures and score <= prev), stops early!
    assert call_count == 2
    assert len(scorecards) == 2

# 7. Test Structured Failure Diagnosis across All Six Categories
def test_diagnose_failures_all_six_categories(base_agent):
    critic = CriticOptimizer(llm_client=MockLLMClient())

    cases = [
        CaseEvaluationResult(
            test_id="TC-RETR", question="Q", passed=False,
            grounding_score=0.0, factual_correctness=0.5, citation_correctness=0.5,
            refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
            failure_reasons=["retrieval_miss: no chunks found"],
            retrieved_sources=[], agent_response="resp"
        ),
        CaseEvaluationResult(
            test_id="TC-CITE", question="Q", passed=False,
            grounding_score=1.0, factual_correctness=1.0, citation_correctness=0.0,
            refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
            failure_reasons=["citation_defect: missing [Source: file]"],
            retrieved_sources=["doc.csv"], agent_response="resp"
        ),
        CaseEvaluationResult(
            test_id="TC-REFUSE", question="Q", passed=False,
            grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
            refusal_correctness=0.0, relevance_score=1.0, output_contract_compliance=1.0,
            failure_reasons=["wrong_refusal: answered out of scope question"],
            retrieved_sources=["doc.csv"], agent_response="resp"
        ),
        CaseEvaluationResult(
            test_id="TC-HALLUC", question="Q", passed=False,
            grounding_score=0.2, factual_correctness=0.5, citation_correctness=1.0,
            refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
            failure_reasons=["hallucination: made up delivery date"],
            retrieved_sources=["doc.csv"], agent_response="resp"
        ),
        CaseEvaluationResult(
            test_id="TC-CONTRACT", question="Q", passed=False,
            grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
            refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=0.0,
            failure_reasons=["output_contract_violation: format is not markdown"],
            retrieved_sources=["doc.csv"], agent_response="resp"
        ),
        CaseEvaluationResult(
            test_id="TC-PROMPT", question="Q", passed=False,
            grounding_score=0.8, factual_correctness=0.5, citation_correctness=0.8,
            refusal_correctness=1.0, relevance_score=0.5, output_contract_compliance=1.0,
            failure_reasons=["prompt_defect: indirect response"],
            retrieved_sources=["doc.csv"], agent_response="resp"
        ),
    ]

    diagnoses = critic.diagnose_failures(cases)
    categories_found = {d.category for d in diagnoses}

    assert "retrieval_miss" in categories_found
    assert "citation_defect" in categories_found
    assert "wrong_refusal" in categories_found
    assert "hallucination" in categories_found
    assert "output_contract_violation" in categories_found
    assert "prompt_defect" in categories_found

    # Verify each diagnosis has root cause, relevant config field, proposed change
    for d in diagnoses:
        assert d.root_cause, "Diagnosis must contain root_cause"
        assert d.relevant_config_field, "Diagnosis must locate relevant_config_field"
        assert isinstance(d.proposed_change, dict), "Proposed change must be a dict"

# 8. Test Repair Validation Safeguard
def test_validate_repair_safeguard(base_agent):
    critic = CriticOptimizer(llm_client=MockLLMClient())

    # Valid change
    assert critic.validate_repair({"target": "top_k", "delta": 1}, base_agent) is True
    assert critic.validate_repair({"target": "similarity_threshold", "secondary_delta": -0.05}, base_agent) is True

    # Invalid target field
    assert critic.validate_repair({"target": "unrelated_secret_key"}, base_agent) is False
    assert critic.validate_repair({"target": "agent_name"}, base_agent) is False

    # Out of bounds numeric changes
    assert critic.validate_repair({"target": "top_k", "delta": 50}, base_agent) is False  # > 12
    assert critic.validate_repair({"target": "similarity_threshold", "secondary_delta": -0.99}, base_agent) is False  # < 0.10

    # Invalid empty system prompt insertion
    assert critic.validate_repair({"target": "system_prompt", "content": ""}, base_agent) is False

def test_detailed_optimization_log_contents(tmp_path, base_agent, mock_eval_set):
    artifacts_dir = tmp_path / "logs_test"
    artifacts_dir.mkdir()

    critic = CriticOptimizer(llm_client=MockLLMClient(), max_iterations=2)

    def mock_eval_logs(eval_set, runner, iteration):
        pass_rate = 0.40 if iteration == 1 else 0.80
        passed_count = int(pass_rate * 5)
        return IterationScorecard(
            iteration=iteration,
            total_tests=5,
            passed_tests=passed_count,
            failed_tests=5 - passed_count,
            pass_rate=pass_rate,
            status="FAIL",
            case_results=[
                CaseEvaluationResult(
                    test_id=f"TEST-00{i}",
                    question=f"Q{i}",
                    passed=(i <= passed_count),
                    grounding_score=1.0 if i <= passed_count else 0.1,
                    factual_correctness=1.0 if i <= passed_count else 0.1,
                    citation_correctness=1.0 if i <= passed_count else 0.1,
                    refusal_correctness=1.0,
                    relevance_score=1.0 if i <= passed_count else 0.5,
                    output_contract_compliance=1.0,
                    failure_reasons=["retrieval_miss: not retrieved"] if i > passed_count else [],
                    agent_response="resp"
                ) for i in range(1, 6)
            ]
        )

    with patch("app.factory.critic_optimizer.HybridJudge.evaluate_eval_set", side_effect=mock_eval_logs):
        final_agent, scorecards, logs = critic.run_optimization_loop(
            initial_agent=base_agent,
            eval_set=mock_eval_set,
            doc_folder=str(tmp_path),
            artifacts_dir=str(artifacts_dir),
            target_pass_rate=0.90
        )

    assert len(logs) >= 1
    log = logs[0]
    assert log.iteration_number == 1
    assert log.previous_score == 0.40
    assert log.new_score == 0.80
    assert log.score_difference == 0.40
    assert "TEST-003" in log.resolved_test_ids or "TEST-004" in log.resolved_test_ids
    assert log.regression_detected is False
    assert log.change_accepted is True
    assert len(log.changes_applied) > 0

    first_change = log.changes_applied[0]
    assert "field" in first_change or "target" in first_change
    assert "previous_value" in first_change
    assert "new_value" in first_change
    assert "reason" in first_change
    assert "affected_tests" in first_change

    # Verify iteration_logs.json file was written
    logs_file = artifacts_dir / "iteration_logs.json"
    assert logs_file.exists()
    with open(logs_file) as f:
        serialized = json.load(f)
        assert len(serialized) == len(logs)
        assert serialized[0]["iteration_number"] == 1
        assert serialized[0]["score_difference"] == 0.40
