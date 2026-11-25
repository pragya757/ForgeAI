import os
import json
import pytest
from typing import List

from app.schemas.requirements import Requirements, DocumentItem
from app.schemas.groundability import (
    GroundabilityReport,
    SupportedTopic,
    PartiallySupportedTopic,
    UnsupportedTopic
)
from app.schemas.agent_definition import (
    AgentDefinition,
    OutputContract,
    CitationRequirements,
    ModelConfig
)
from app.schemas.evaluation import EvalSet, EvalCase
from app.schemas.scorecard import CaseEvaluationResult, IterationScorecard, IterationLog
from app.factory.reporter import HonestReportGenerator

@pytest.fixture
def mock_requirements():
    return Requirements(
        agent_name="Maritime Technical Spare Parts Assistant",
        purpose="Assist vessel superintendents with marine machinery spares procurement.",
        target_audience="Marine Engineers, Technical Superintendents, Fleet Purchasing Managers",
        scope="Inquiries regarding marine fuel pumps, purifier spares, overhaul kits, and supplier lead times.",
        tone="Technical, factual, professional",
        must_answer_topics=[
            "Main Engine Fuel Oil Delivery Pump specifications",
            "Rotterdam warehouse stock levels",
            "Lead times and catalog unit pricing"
        ],
        must_refuse_topics=[
            "Crew salary inquiries",
            "International bank wire transfers",
            "Maritime insurance claims"
        ],
        required_tools=["csv_lookup", "current_date"],
        document_inventory=[
            DocumentItem(
                filename="spare_parts_catalog.csv",
                format="CSV",
                page_count=50,
                description="Marine vessel machinery spare parts price list and inventory counts.",
                detected_topics=["Part numbers", "Pricing", "Warehouse availability"]
            ),
            DocumentItem(
                filename="procurement_policy.pdf",
                format="PDF",
                page_count=12,
                description="Technical procurement protocol and delivery terms.",
                detected_topics=["Lead times", "Shipping terms"]
            )
        ],
        assumptions=["Prices quoted in USD", "Rotterdam is primary transit depot"],
        ambiguities=["Standard sea freight delivery duration vs express air freight"],
        unsupported_requirements=["Crew payroll administration"]
    )

@pytest.fixture
def mock_groundability():
    return GroundabilityReport(
        overall_groundability_score=0.88,
        sanitized_answerable_topics=[
            "Main Engine Fuel Oil Delivery Pump specifications",
            "Rotterdam warehouse stock levels"
        ],
        supported_topics=[
            SupportedTopic(
                topic="Main Engine Fuel Oil Delivery Pump specifications",
                evidence_sources=["spare_parts_catalog.csv"],
                confidence_score=0.95,
                coverage_summary="Full technical specs and part numbers cataloged."
            ),
            SupportedTopic(
                topic="Rotterdam warehouse stock levels",
                evidence_sources=["spare_parts_catalog.csv"],
                confidence_score=0.92,
                coverage_summary="Stock counts available per line item."
            )
        ],
        partially_supported_topics=[
            PartiallySupportedTopic(
                topic="Lead times and catalog unit pricing",
                evidence_sources=["procurement_policy.pdf"],
                missing_aspects="Express air freight rates are unlisted."
            )
        ],
        unsupported_topics=[
            UnsupportedTopic(
                topic="Crew salary inquiries",
                reason="Personnel compensation data does not exist in technical parts catalog.",
                absence_nature="missing_from_corpus"
            ),
            UnsupportedTopic(
                topic="International bank wire transfers",
                reason="Financial wire instructions cannot be authorized by automated retrieval agents.",
                absence_nature="unsupported_capability"
            )
        ],
        document_coverage_map={"spare_parts_catalog.csv": ["Part numbers", "Stock levels"]},
        refusal_recommendations=["Refuse crew payroll and financial transfers."]
    )

@pytest.fixture
def mock_agent():
    return AgentDefinition(
        agent_name="Maritime Technical Spare Parts Assistant",
        description="Assists vessel superintendents with marine machinery spares procurement.",
        system_prompt="Answer procurement inquiries strictly from technical manuals.",
        target_audience="Marine Engineers, Technical Superintendents",
        supported_topics=["Spare parts pricing", "Stock levels"],
        unsupported_topics=["Crew salary inquiries", "International bank wire transfers"],
        must_refuse_topics=["Crew salary inquiries", "International bank wire transfers"],
        document_references=["spare_parts_catalog.csv", "procurement_policy.pdf"],
        chunk_size=450,
        chunk_overlap=90,
        top_k=4,
        similarity_threshold=0.35,
        output_contract=OutputContract(format="markdown"),
        citation_requirements=CitationRequirements(mandatory=True, tag_format="[Source: <filename>]"),
        tool_selection=["csv_lookup"],
        tool_justifications={"csv_lookup": "Allows exact row-level lookups for spare part inventory numbers."},
        refusal_policy="Strict",
        model_config=ModelConfig()
    )

@pytest.fixture
def mock_scorecards():
    # Iteration 1 (Baseline)
    case_results_1 = [
        CaseEvaluationResult(
            test_id="TC-001",
            question="What is the unit price of NV-PUMP-001?",
            passed=True,
            outcome_classification="correct_with_evidence",
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=1.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            agent_response="Part NV-PUMP-001 is $4,250.00 USD. [Source: spare_parts_catalog.csv]",
            retrieved_sources=["spare_parts_catalog.csv"]
        ),
        CaseEvaluationResult(
            test_id="TC-002",
            question="What is the CEO salary?",
            passed=False,
            outcome_classification="incorrect_refusal",
            grounding_score=0.2,
            factual_correctness=0.0,
            citation_correctness=0.0,
            refusal_correctness=0.0,
            relevance_score=0.5,
            output_contract_compliance=1.0,
            failure_reasons=["wrong_refusal: Expected refusal for out-of-scope inquiry."],
            evidence_reasoning="Model attempted to speculate rather than refusing.",
            agent_response="The CEO salary might be around $500,000.",
            retrieved_sources=[]
        ),
        CaseEvaluationResult(
            test_id="TC-003",
            question="Where is stock held?",
            passed=False,
            outcome_classification="correct_without_evidence",
            grounding_score=0.6,
            factual_correctness=1.0,
            citation_correctness=0.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            failure_reasons=["citation_defect: Response omitted mandatory citation tag."],
            evidence_reasoning="Correct facts stated but omitted mandatory [Source: doc] tag.",
            agent_response="Stock is held in the Rotterdam warehouse.",
            retrieved_sources=["spare_parts_catalog.csv"]
        )
    ]
    sc1 = IterationScorecard(
        iteration=1,
        total_tests=3,
        passed_tests=1,
        failed_tests=2,
        pass_rate=0.3333,
        metric_breakdown={
            "grounding": 0.60,
            "factual_correctness": 0.67,
            "citation_correctness": 0.33,
            "refusal_correctness": 0.67,
            "relevance": 0.83,
            "output_contract_compliance": 1.0
        },
        status="FAIL",
        case_results=case_results_1
    )

    # Iteration 2 (Optimized)
    case_results_2 = [
        CaseEvaluationResult(
            test_id="TC-001",
            question="What is the unit price of NV-PUMP-001?",
            passed=True,
            outcome_classification="correct_with_evidence",
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=1.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            agent_response="Part NV-PUMP-001 is $4,250.00 USD. [Source: spare_parts_catalog.csv]",
            retrieved_sources=["spare_parts_catalog.csv"]
        ),
        CaseEvaluationResult(
            test_id="TC-002",
            question="What is the CEO salary?",
            passed=True,
            outcome_classification="correct_refusal",
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=1.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            agent_response="I cannot answer this question as executive compensation is outside verified documentation scope. [Source: Policy Limitations]",
            retrieved_sources=[]
        ),
        CaseEvaluationResult(
            test_id="TC-003",
            question="Where is stock held?",
            passed=True,
            outcome_classification="correct_with_evidence",
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=1.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            agent_response="Stock is held in the Rotterdam warehouse. [Source: spare_parts_catalog.csv]",
            retrieved_sources=["spare_parts_catalog.csv"]
        )
    ]
    sc2 = IterationScorecard(
        iteration=2,
        total_tests=3,
        passed_tests=3,
        failed_tests=0,
        pass_rate=1.0,
        metric_breakdown={
            "grounding": 1.0,
            "factual_correctness": 1.0,
            "citation_correctness": 1.0,
            "refusal_correctness": 1.0,
            "relevance": 1.0,
            "output_contract_compliance": 1.0
        },
        status="PASS",
        case_results=case_results_2
    )
    return [sc1, sc2]

@pytest.fixture
def mock_iteration_logs():
    return [
        IterationLog(
            iteration_number=1,
            previous_score=0.3333,
            new_score=1.0,
            score_difference=0.6667,
            failed_test_ids=["TC-002", "TC-003"],
            failure_categories=["wrong_refusal", "citation_defect"],
            identified_root_causes="Ambiguous refusal boundaries and omitted inline citation directives.",
            changes_applied=[
                {
                    "target": "system_prompt (citation clause)",
                    "field": "system_prompt",
                    "previous_value": "standard prompt",
                    "new_value": "appended strict citation tag directive",
                    "reason": "Enforce explicit [Source: filename] tagging.",
                    "affected_tests": ["TC-003"]
                },
                {
                    "target": "system_prompt (refusal policy)",
                    "field": "system_prompt",
                    "previous_value": "standard refusal policy",
                    "new_value": "clarified refusal criteria for unverified compensation topics",
                    "reason": "Strictly refuse out-of-scope inquiries.",
                    "affected_tests": ["TC-002"]
                }
            ],
            reason_for_each_change="Targeted adjustments to resolve identified failure modes.",
            updated_configuration={"top_k": 4, "similarity_threshold": 0.35},
            resolved_test_ids=["TC-002", "TC-003"],
            regressed_test_ids=[],
            regression_detected=False,
            change_accepted=True,
            improvement_or_regression="IMPROVED (+66.7%)"
        )
    ]

# 1. Test Markdown and JSON Reports Generation
def test_reports_generated_in_both_markdown_and_json(
    tmp_path,
    mock_requirements,
    mock_groundability,
    mock_agent,
    mock_scorecards,
    mock_iteration_logs
):
    out_dir = tmp_path / "report_out"
    reporter = HonestReportGenerator()

    report_md = reporter.generate_report(
        brief="Create an assistant for technical ship operations and spare parts procurement.",
        requirements=mock_requirements,
        groundability=mock_groundability,
        final_agent=mock_agent,
        scorecards=mock_scorecards,
        iteration_logs=mock_iteration_logs,
        output_dir=str(out_dir)
    )

    # Verify both Markdown and JSON files are written
    assert os.path.exists(out_dir / "final_report.md")
    assert os.path.exists(out_dir / "quality_report.json")
    assert os.path.exists(out_dir / "final_report.json")
    assert os.path.exists(out_dir / "scorecards.json")
    assert os.path.exists(out_dir / "iteration_logs.json")

    # Verify return value is the Markdown string
    assert isinstance(report_md, str)
    assert len(report_md) > 500

    # Verify JSON report is valid structured JSON
    with open(out_dir / "quality_report.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["agent_name"] == mock_agent.agent_name
        assert data["final_status"] == "PRODUCTION_READY"
        assert "before_and_after_comparison" in data
        assert "reproducible_metrics" in data

# 2. Test All 14 Mandatory Sections in the Report
def test_all_fourteen_mandatory_sections_included(
    tmp_path,
    mock_requirements,
    mock_groundability,
    mock_agent,
    mock_scorecards,
    mock_iteration_logs
):
    out_dir = tmp_path / "sections_out"
    reporter = HonestReportGenerator()

    report_md = reporter.generate_report(
        brief="Create an assistant for technical ship operations.",
        requirements=mock_requirements,
        groundability=mock_groundability,
        final_agent=mock_agent,
        scorecards=mock_scorecards,
        iteration_logs=mock_iteration_logs,
        output_dir=str(out_dir)
    )

    # Verify all 14 mandatory sections are present as numbered headings
    assert "## 1. Original User Brief" in report_md
    assert "## 2. Document Inventory" in report_md
    assert "## 3. Structured Requirements" in report_md
    assert "## 4. Groundability Guard Analysis" in report_md
    assert "## 5. Generated Agent Configuration" in report_md
    assert "## 6. Selected Tools & Justification" in report_md
    assert "## 7. Evaluation Dataset Summary" in report_md
    assert "## 8. Baseline Initial Scorecard" in report_md
    assert "## 9. Optimization Iteration History" in report_md
    assert "## 10. Before-and-After Score Comparison" in report_md
    assert "## 11. Remaining Failed Cases & Raw Audit Logs" in report_md
    assert "## 12. Unsupported Topics & Refusal Policy" in report_md
    assert "## 13. Known Limitations & Operational Boundaries" in report_md
    assert "## 14. Final Agent Status & Reproducibility Verification" in report_md

# 3. Test All Six Required Metrics Computed Accurately
def test_all_six_metrics_computed_accurately():
    reporter = HonestReportGenerator()

    case_results = [
        CaseEvaluationResult(
            test_id="T1", question="Q1", passed=True,
            grounding_score=1.0, factual_correctness=1.0, citation_correctness=1.0,
            refusal_correctness=1.0, relevance_score=1.0, output_contract_compliance=1.0,
            agent_response="resp"
        ),
        CaseEvaluationResult(
            test_id="T2", question="Q2", passed=False,
            grounding_score=0.4, factual_correctness=0.6, citation_correctness=0.0,
            refusal_correctness=1.0, relevance_score=0.8, output_contract_compliance=0.5,
            agent_response="resp"
        )
    ]

    metrics = reporter.compute_reproducible_metrics(case_results)

    # 1. Overall Pass Rate: 1 / 2 = 0.5
    assert metrics["overall_pass_rate"] == 0.50
    # 2. Grounded Answer Rate: (1.0 + 0.4) / 2 = 0.70
    assert metrics["grounded_answer_rate"] == 0.70
    # 3. Factual Correctness: (1.0 + 0.6) / 2 = 0.80
    assert metrics["factual_correctness"] == 0.80
    # 4. Correct Refusal Rate: (1.0 + 1.0) / 2 = 1.00
    assert metrics["correct_refusal_rate"] == 1.00
    # 5. Citation Accuracy: (1.0 + 0.0) / 2 = 0.50
    assert metrics["citation_accuracy"] == 0.50
    # 6. Output-Contract Compliance: (1.0 + 0.5) / 2 = 0.75
    assert metrics["output_contract_compliance"] == 0.75

# 4. Test Mathematical Reproducibility from Saved Results
def test_scores_strictly_reproducible_from_saved_results(
    tmp_path,
    mock_requirements,
    mock_groundability,
    mock_agent,
    mock_scorecards,
    mock_iteration_logs
):
    out_dir = tmp_path / "reproducible_test"
    reporter = HonestReportGenerator()

    reporter.generate_report(
        brief="Create an assistant for technical ship operations.",
        requirements=mock_requirements,
        groundability=mock_groundability,
        final_agent=mock_agent,
        scorecards=mock_scorecards,
        iteration_logs=mock_iteration_logs,
        output_dir=str(out_dir)
    )

    # Load serialized scorecards and JSON report
    with open(out_dir / "scorecards.json", "r") as f:
        scorecards_json = json.load(f)

    with open(out_dir / "quality_report.json", "r") as f:
        report_json = json.load(f)

    final_sc_data = scorecards_json[-1]
    final_cases = [CaseEvaluationResult(**c) for c in final_sc_data["case_results"]]

    # Re-compute metrics directly from the raw saved case results
    recomputed = reporter.compute_reproducible_metrics(final_cases)

    # Verify exact parity with the numbers documented in the report
    for metric_name, value in recomputed.items():
        assert report_json["reproducible_metrics"][metric_name] == value, (
            f"Reproducibility violation on {metric_name}: saved={report_json['reproducible_metrics'][metric_name]} vs recomputed={value}"
        )

# 5. Test Preservation of Raw Test Responses and Judge Decisions for Auditing
def test_raw_test_responses_and_judge_decisions_preserved(
    tmp_path,
    mock_requirements,
    mock_groundability,
    mock_agent,
    mock_scorecards,
    mock_iteration_logs
):
    out_dir = tmp_path / "audit_test"
    reporter = HonestReportGenerator()

    # Pass only Iteration 1 scorecard (which contains 2 failed cases) to inspect failed case auditing
    reporter.generate_report(
        brief="Create an assistant for technical ship operations.",
        requirements=mock_requirements,
        groundability=mock_groundability,
        final_agent=mock_agent,
        scorecards=[mock_scorecards[0]],
        iteration_logs=[],
        output_dir=str(out_dir)
    )

    with open(out_dir / "quality_report.json", "r") as f:
        report_data = json.load(f)

    remaining_failures = report_data["remaining_failed_cases"]
    assert len(remaining_failures) == 2, "Must not omit any failed cases"

    # Check that raw agent response and judge reasoning are preserved in full
    failed_tc2 = next(c for c in remaining_failures if c["test_id"] == "TC-002")
    assert "CEO salary might be around $500,000" in failed_tc2["raw_agent_response"]
    assert "wrong_refusal" in failed_tc2["failure_reasons"][0]
    assert failed_tc2["judge_evidence_reasoning"] == "Model attempted to speculate rather than refusing."

    failed_tc3 = next(c for c in remaining_failures if c["test_id"] == "TC-003")
    assert "Rotterdam warehouse" in failed_tc3["raw_agent_response"]
    assert "citation_defect" in failed_tc3["failure_reasons"][0]

    # Verify Markdown also preserves raw agent response in code blocks
    with open(out_dir / "final_report.md", "r") as f:
        md_text = f.read()
        assert "TC-002" in md_text
        assert "The CEO salary might be around $500,000" in md_text
        assert "TC-003" in md_text

# 6. Test Zero Fabrication & Zero Silent Omission
def test_zero_silent_omission_when_all_pass(
    tmp_path,
    mock_requirements,
    mock_groundability,
    mock_agent,
    mock_scorecards,
    mock_iteration_logs
):
    out_dir = tmp_path / "zero_omission_test"
    reporter = HonestReportGenerator()

    # Pass scorecard with 100% pass rate
    reporter.generate_report(
        brief="Create an assistant for technical ship operations.",
        requirements=mock_requirements,
        groundability=mock_groundability,
        final_agent=mock_agent,
        scorecards=[mock_scorecards[1]],  # 100% pass
        iteration_logs=mock_iteration_logs,
        output_dir=str(out_dir)
    )

    with open(out_dir / "quality_report.json", "r") as f:
        report_data = json.load(f)

    assert len(report_data["remaining_failed_cases"]) == 0

    with open(out_dir / "final_report.md", "r") as f:
        md_text = f.read()
        assert "Zero remaining defects detected" in md_text
