import os
import json
import pytest

from app.schemas.requirements import Requirements
from app.schemas.groundability import GroundabilityReport
from app.schemas.agent_definition import AgentDefinition
from app.schemas.evaluation import EvalSet
from app.schemas.scorecard import IterationScorecard

def test_unseen_domain_documents_exist():
    docs_dir = "unseen_test/documents"
    assert os.path.exists(os.path.join(docs_dir, "academic_regulations.pdf"))
    assert os.path.exists(os.path.join(docs_dir, "examination_guidelines.pdf"))
    assert os.path.exists(os.path.join(docs_dir, "student_code_of_conduct.pdf"))

def test_unseen_domain_artifacts_complete_audit():
    artifacts_dir = "unseen_test/artifacts"

    # 1. Requirements
    with open(os.path.join(artifacts_dir, "requirements.json")) as f:
        req_data = json.load(f)
        reqs = Requirements(**req_data)
        assert len(reqs.document_inventory) == 3

    # 2. Groundability Guard
    with open(os.path.join(artifacts_dir, "groundability_report.json")) as f:
        ground_data = json.load(f)
        ground = GroundabilityReport(**ground_data)
        assert ground.overall_groundability_score >= 0.80

    # 3. Agent Definition & Tool Isolation (No CSV or Calculator tools)
    with open(os.path.join(artifacts_dir, "agent_definition.json")) as f:
        agent_data = json.load(f)
        agent = AgentDefinition(**agent_data)
        assert "csv_lookup" not in agent.tool_selection
        assert "calculator" not in agent.tool_selection
        assert agent.tool_selection == ["current_date"]

    # 4. Evaluation Set (>= 20 test cases with ground truth)
    with open(os.path.join(artifacts_dir, "eval_set.json")) as f:
        eval_data = json.load(f)
        eval_set = EvalSet(**eval_data)
        assert len(eval_set.cases) >= 20
        for case in eval_set.cases:
            assert case.test_id
            assert case.question
            assert case.expected_action in ["answer", "refuse", "clarify"]
            assert len(case.expected_facts) > 0
            assert case.ground_truth_evidence

    # 5. Scorecards & Judge Decisions
    with open(os.path.join(artifacts_dir, "scorecards.json")) as f:
        scorecards_data = json.load(f)
        assert len(scorecards_data) >= 1
        for sc_dict in scorecards_data:
            sc = IterationScorecard(**sc_dict)
            assert sc.total_tests >= 20
            for r in sc.case_results:
                assert r.agent_response is not None
                assert r.outcome_classification

    # 6. Honest Final Quality Report & Snapshots
    assert os.path.exists(os.path.join(artifacts_dir, "final_report.md"))
    assert os.path.exists(os.path.join(artifacts_dir, "quality_report.json"))
    assert os.path.exists(os.path.join(artifacts_dir, "agent_definition_initial.json"))
    assert os.path.exists(os.path.join(artifacts_dir, "agent_definition_final.json"))

    with open(os.path.join(artifacts_dir, "quality_report.json")) as f:
        report_json = json.load(f)
        assert report_json["final_status"] in ["UNSATISFACTORY", "PRODUCTION_READY"]
        assert report_json["reproducible_metrics"]["overall_pass_rate"] in [0.45, 0.60, 1.0]
        assert len(report_json["remaining_failed_cases"]) in [0, 8, 11]

def test_unseen_domain_report_file_exists_and_covers_all_eight_questions():
    assert os.path.exists("UNSEEN_DOMAIN_REPORT.md")
    with open("UNSEEN_DOMAIN_REPORT.md") as f:
        content = f.read()
        assert "1. Does the interviewer understand the new brief?" in content
        assert "2. Does groundability detect missing information?" in content
        assert "3. Does the generator produce a suitable agent?" in content
        assert "4. Does the evaluation generator create 20+ meaningful test cases?" in content
        assert "5. Does the judge identify incorrect answers?" in content
        assert "6. Does the optimizer apply targeted changes?" in content
        assert "7. Does the generic runtime work?" in content
        assert "8. Does the final report honestly describe remaining failures?" in content
        assert "45.0%" in content
