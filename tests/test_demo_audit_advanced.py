import os
import json
import pytest

from app.schemas.requirements import Requirements
from app.schemas.groundability import GroundabilityReport
from app.schemas.agent_definition import AgentDefinition
from app.schemas.evaluation import EvalSet
from app.schemas.scorecard import IterationScorecard

def test_demo1_hr_assistant_artifacts_complete_audit():
    artifacts_dir = "demos/hr_assistant/artifacts"
    docs_dir = "demos/hr_assistant/documents"

    # 1. Original documents exist
    assert os.path.exists(os.path.join(docs_dir, "leave_policy.pdf"))
    assert os.path.exists(os.path.join(docs_dir, "attendance_policy.pdf"))
    assert os.path.exists(os.path.join(docs_dir, "employee_handbook.pdf"))

    # 2. Requirements generated and valid
    with open(os.path.join(artifacts_dir, "requirements.json")) as f:
        req_data = json.load(f)
        reqs = Requirements(**req_data)
        assert reqs.agent_name == "HR Policy Assistant"
        assert len(reqs.must_answer_topics) >= 3
        assert len(reqs.must_refuse_topics) >= 2
        assert len(reqs.document_inventory) == 3

    # 3. Groundability Guard analysis
    with open(os.path.join(artifacts_dir, "groundability_report.json")) as f:
        ground_data = json.load(f)
        ground = GroundabilityReport(**ground_data)
        assert ground.overall_groundability_score >= 0.80
        assert len(ground.supported_topics) > 0
        assert len(ground.unsupported_topics) > 0

    # 4. Agent Definition & Strict Tool Isolation (NO procurement tools!)
    with open(os.path.join(artifacts_dir, "agent_definition.json")) as f:
        agent_data = json.load(f)
        agent = AgentDefinition(**agent_data)
        assert agent.agent_name == "HR Policy Assistant"
        # Tool isolation: NO csv_lookup, NO calculator, NO weather
        assert "csv_lookup" not in agent.tool_selection
        assert "calculator" not in agent.tool_selection
        assert "weather" not in agent.tool_selection
        assert agent.tool_selection == ["current_date"]

    # 5. Evaluation Dataset (>= 20 test cases with source evidence)
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

    # 6. Scorecards & Raw Responses / Decisions
    with open(os.path.join(artifacts_dir, "scorecards.json")) as f:
        scorecards_data = json.load(f)
        assert len(scorecards_data) >= 1
        for sc_dict in scorecards_data:
            sc = IterationScorecard(**sc_dict)
            assert sc.total_tests >= 20
            for r in sc.case_results:
                assert r.agent_response, f"Missing agent_response in test {r.test_id}"
                assert r.outcome_classification

    # 7. Final Reports
    assert os.path.exists(os.path.join(artifacts_dir, "final_report.md"))
    assert os.path.exists(os.path.join(artifacts_dir, "quality_report.json"))
    with open(os.path.join(artifacts_dir, "final_report.md")) as f:
        md_text = f.read()
        assert "## 1. Original User Brief" in md_text
        assert "## 14. Final Agent Status" in md_text

def test_demo2_procurement_assistant_artifacts_complete_audit():
    artifacts_dir = "demos/procurement_assistant/artifacts"
    docs_dir = "demos/procurement_assistant/documents"

    # 1. Original documents exist
    assert os.path.exists(os.path.join(docs_dir, "spare_parts_catalog.csv"))
    assert os.path.exists(os.path.join(docs_dir, "procurement_guidelines.pdf"))
    assert os.path.exists(os.path.join(docs_dir, "supplier_information.pdf"))

    # 2. Requirements generated and valid
    with open(os.path.join(artifacts_dir, "requirements.json")) as f:
        req_data = json.load(f)
        reqs = Requirements(**req_data)
        assert reqs.agent_name == "Ship-Spares Procurement Assistant"
        assert len(reqs.must_answer_topics) >= 3
        assert len(reqs.must_refuse_topics) >= 2

    # 3. Groundability Guard analysis
    with open(os.path.join(artifacts_dir, "groundability_report.json")) as f:
        ground_data = json.load(f)
        ground = GroundabilityReport(**ground_data)
        assert ground.overall_groundability_score >= 0.80

    # 4. Agent Definition & Justified Tool Selection (csv_lookup & calculator justified)
    with open(os.path.join(artifacts_dir, "agent_definition.json")) as f:
        agent_data = json.load(f)
        agent = AgentDefinition(**agent_data)
        assert agent.agent_name == "Ship-Spares Procurement Assistant"
        assert "csv_lookup" in agent.tool_selection
        assert "calculator" in agent.tool_selection
        # Must have justifications
        assert "csv_lookup" in agent.tool_justifications
        assert "calculator" in agent.tool_justifications

    # 5. Evaluation Dataset (>= 20 test cases with source evidence)
    with open(os.path.join(artifacts_dir, "eval_set.json")) as f:
        eval_data = json.load(f)
        eval_set = EvalSet(**eval_data)
        assert len(eval_set.cases) >= 20
        for case in eval_set.cases:
            assert case.test_id
            assert case.question
            assert len(case.expected_facts) > 0
            assert case.ground_truth_evidence

    # 6. Scorecards & Raw Responses / Decisions
    with open(os.path.join(artifacts_dir, "scorecards.json")) as f:
        scorecards_data = json.load(f)
        assert len(scorecards_data) >= 1
        for sc_dict in scorecards_data:
            sc = IterationScorecard(**sc_dict)
            assert sc.total_tests >= 20
            for r in sc.case_results:
                assert r.agent_response, f"Missing agent_response in test {r.test_id}"
                assert r.outcome_classification

    # 7. Final Reports
    assert os.path.exists(os.path.join(artifacts_dir, "final_report.md"))
    assert os.path.exists(os.path.join(artifacts_dir, "quality_report.json"))
    with open(os.path.join(artifacts_dir, "final_report.md")) as f:
        md_text = f.read()
        assert "## 1. Original User Brief" in md_text
        assert "## 6. Selected Tools & Justification" in md_text
        assert "## 14. Final Agent Status" in md_text

def test_demo_readme_documentation_exists_and_verified():
    assert os.path.exists("DEMO_README.md")
    with open("DEMO_README.md") as f:
        content = f.read()
        assert "DEMO 1: HR Policy Assistant" in content
        assert "DEMO 2: Ship-Spares Procurement Assistant" in content
        assert "csv_lookup" in content
        assert "calculator" in content
        assert "current_date" in content
        assert "python run_factory.py" in content
        assert "python run_agent.py" in content
