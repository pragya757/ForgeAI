import os
import json
import pytest
from app.llm.mock_client import MockLLMClient
from app.factory.interviewer import IntakeInterviewer, GENERIC_STOPWORDS
from app.factory.groundability import GroundabilityGuard
from app.factory.agent_generator import AgentGenerator
from app.factory.eval_generator import AutomaticEvalGenerator
from app.factory.pipeline import ForgeAIFactory
from app.runtime.chat_runner import GenericChatRunner
from app.schemas.scorecard import IterationLog, IterationScorecard, CaseEvaluationResult
from streamlit_app import safe_to_dict, safe_to_dict_list


def test_iteration_log_pydantic_and_dict_compatibility():
    """Verify that safe_to_dict correctly parses both Pydantic IterationLog and raw dicts without AttributeError."""
    pydantic_log = IterationLog(
        iteration_number=2,
        previous_score=0.75,
        failed_test_ids=["TC-004", "TC-009"],
        failure_categories=["citation_defect", "retrieval_truncation"],
        identified_root_causes="Missing exact page citations in generated answers.",
        changes_applied=[
            {"target": "top_k", "previous_value": 3, "new_value": 5, "reason": "Expand retrieval"},
            {"target": "system_prompt", "previous_value": "old", "new_value": "new", "reason": "Enforce citations"}
        ],
        reason_for_each_change="Resolve grounding and citation failures",
        updated_configuration={"top_k": 5},
        new_score=0.90,
        improvement_or_regression="IMPROVED",
        score_difference=0.15,
        resolved_test_ids=["TC-004", "TC-009"],
        regressed_test_ids=[],
        regression_detected=False,
        change_accepted=True
    )

    # Test conversion from Pydantic model
    d_pydantic = safe_to_dict(pydantic_log)
    assert isinstance(d_pydantic, dict)
    assert d_pydantic.get("iteration_number") == 2
    assert d_pydantic.get("previous_score") == 0.75
    assert d_pydantic.get("new_score") == 0.90
    assert "Missing exact page citations" in d_pydantic.get("identified_root_causes")
    assert len(d_pydantic.get("changes_applied")) == 2

    # Test conversion from legacy / alternative dict
    legacy_dict = {
        "iteration": 1,
        "score_before": 0.60,
        "score_after": 0.80,
        "root_cause_diagnosis": "Threshold mismatch",
        "failure_category": "factual_error",
        "changes_applied": [{"target": "temperature", "new_value": 0.1}]
    }
    d_legacy = safe_to_dict(legacy_dict)
    assert isinstance(d_legacy, dict)
    assert d_legacy.get("iteration") == 1
    assert d_legacy.get("score_before") == 0.60
    assert d_legacy.get("score_after") == 0.80

    # Test list conversion
    logs_list = safe_to_dict_list([pydantic_log, legacy_dict])
    assert len(logs_list) == 2
    assert all(isinstance(l, dict) for l in logs_list)


def test_clarifying_questions_generic_stopwords_filtered():
    """Verify that instruction, meta words, and constraint words are filtered out of gap detection."""
    instruction_words = [
        "create", "assistant", "company", "answers", "using", "policy", "guidelines", "documents",
        "accurate", "acknowledge", "answered", "cannot", "clearly", "autonomous", "domain", "uploaded",
        "citation", "citations", "refuse", "missing", "understand"
    ]
    for word in instruction_words:
        assert word in GENERIC_STOPWORDS, f"'{word}' must be in GENERIC_STOPWORDS"


def test_clarifying_questions_filters_meta_instructions_from_user_brief(tmp_path):
    """Verify that user brief instructions do not trigger false positive gap questions."""
    doc_dir = tmp_path / "univ_docs"
    doc_dir.mkdir()
    (doc_dir / "regulations.txt").write_text(
        "ST. JUDE UNIVERSITY REGULATIONS\n"
        "Graduation requires 120 credits and a CGPA of 2.00.\n"
        "Attendance requires arriving 15 minutes before exams.\n"
        "Grade appeals must be submitted within 10 days with a $50 fee.\n"
    )

    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    brief = (
        "Create a University Regulations Assistant that helps students and faculty understand academic regulations, "
        "attendance, appeals and graduation. The assistant must answer using only the uploaded university regulations "
        "document, provide accurate source citations, and clearly refuse or acknowledge missing information when a "
        "question cannot be answered from the document."
    )

    questions = interviewer.generate_clarifying_questions(brief=brief, doc_folder=str(doc_dir))
    assert len(questions) == 0, f"Expected 0 questions for clear brief with instruction words, got: {questions}"


def test_clarifying_questions_clear_brief_returns_empty(tmp_path):
    """Verify that a clear, comprehensive brief with fully-grounded files returns 0 questions."""
    doc_dir = tmp_path / "clear_docs"
    doc_dir.mkdir()
    doc_file = doc_dir / "engineering_handbook.txt"
    doc_file.write_text(
        "ENGINEERING HANDBOOK\n"
        "Deployment Procedure: All production pull requests require two peer approvals.\n"
        "On-Call Rotation: Primary on-call shifts rotate weekly on Monday at 09:00 UTC.\n"
        "Incident Severity: Severity 1 incidents mandate an emergency bridge within 15 minutes.\n"
    )

    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    brief = "Create an engineering handbook assistant that answers developer questions about deployment procedures, on-call rotations, and incident severity using engineering documents."

    questions = interviewer.generate_clarifying_questions(brief=brief, doc_folder=str(doc_dir))
    assert isinstance(questions, list)
    assert len(questions) == 0, f"Expected 0 questions for a fully-grounded clear brief, got: {questions}"


def test_clarifying_questions_ambiguous_brief_capped_at_five(tmp_path):
    """Verify that ambiguous briefs with missing scope or contradictions formulate <= 5 targeted questions."""
    doc_dir = tmp_path / "ambiguous_docs"
    doc_dir.mkdir()
    (doc_dir / "spec_a.txt").write_text("Operating Ceiling: 3000m maximum depth rated hull.")
    (doc_dir / "spec_b.txt").write_text("Operating Ceiling: 4500m emergency depth rated hull.")

    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    brief = "Assist ROV pilots with depth ceiling, emergency ascent, and ionosphere solar flare telemetry."

    questions = interviewer.generate_clarifying_questions(brief=brief, doc_folder=str(doc_dir))
    assert isinstance(questions, list)
    assert 1 <= len(questions) <= 5
    combined_q = " ".join(questions).lower()
    assert "depth" in combined_q or "precedence" in combined_q or "ceiling" in combined_q or "telemetry" in combined_q


def test_hr_brief_with_unrelated_uploaded_doc_prevents_contamination(tmp_path):
    """Verify that when an HR brief is submitted with an unrelated uploaded file (e.g., IT Interns JD),
    ForgeAI does NOT hallucinate HR demo documents (leave_policy.pdf, attendance_policy.pdf),
    and strictly grounds against the active uploaded file.
    """
    doc_dir = tmp_path / "it_interns"
    doc_dir.mkdir()
    jd_file = doc_dir / "IT_Interns_JD.txt"
    jd_file.write_text(
        "JOB DESCRIPTION: IT SYSTEMS INTERN\n"
        "Role: Assist the infrastructure team with Linux server provisioning and Docker orchestration.\n"
        "Duration: 6-month full-time internship program.\n"
        "Stipend: $2,500 monthly educational allowance.\n"
        "Required Skills: Python scripting, Bash, Git, and Linux administration basics.\n"
        "Supervisor: Reports directly to the Senior DevOps Lead.\n"
    )

    client = MockLLMClient()
    interviewer = IntakeInterviewer(llm_client=client)

    # Use an HR-style brief to intentionally test contamination prevention
    hr_brief = "Create an HR assistant that answers questions about leave policies, attendance, holidays and workplace guidelines using company documents."

    requirements = interviewer.conduct_interview(
        brief=hr_brief,
        doc_folder=str(doc_dir),
        unattended=True
    )

    # Document inventory must reflect IT_Interns_JD.txt, NOT leave_policy.pdf!
    doc_names = [d.filename for d in requirements.document_inventory]
    assert "IT_Interns_JD.txt" in doc_names
    assert "leave_policy.pdf" not in doc_names
    assert "attendance_policy.pdf" not in doc_names
    assert "employee_handbook.pdf" not in doc_names

    # Groundability Guard must also inspect IT_Interns_JD.txt
    guard = GroundabilityGuard(llm_client=client)
    groundability = guard.inspect_groundability(requirements=requirements, doc_folder=str(doc_dir))
    assert "leave_policy.pdf" not in groundability.document_coverage_map
    assert any("IT_Interns_JD.txt" in d for d in groundability.document_coverage_map.keys())

    # Agent Generator must cite IT_Interns_JD.txt, NOT leave_policy.pdf
    generator = AgentGenerator(llm_client=client)
    agent_def = generator.generate_agent(requirements=requirements, groundability=groundability, doc_folder=str(doc_dir))
    assert "leave_policy.pdf" not in agent_def.document_references
    assert any("IT_Interns_JD.txt" in ref for ref in agent_def.document_references)

    # Evaluation Generator must synthesize cases for IT_Interns_JD.txt, NOT TC-001 from HR demo
    eval_gen = AutomaticEvalGenerator(llm_client=client)
    eval_set, _ = eval_gen.generate_evaluation_set(agent_def=agent_def, doc_folder=str(doc_dir), target_count=20)
    assert len(eval_set.cases) >= 20
    for case in eval_set.cases:
        assert "leave_policy.pdf" not in case.expected_sources


def test_consecutive_runs_corpus_isolation(tmp_path):
    """Verify that running two separate pipelines sequentially creates isolated artifact trees without data leakage."""
    # Run 1: Domain 1 (Maritime Logistics)
    dir1 = tmp_path / "domain_1_docs"
    dir1.mkdir()
    (dir1 / "vessel_log.txt").write_text("Vessel Orion voyage 104 departed Singapore anchored in Rotterdam.")

    art1 = tmp_path / "domain_1_artifacts"

    factory = ForgeAIFactory(max_iterations=1)
    res1 = factory.build_agent(
        brief="Assistant for vessel voyages and anchoring operations.",
        doc_folder=str(dir1),
        output_dir=str(art1),
        unattended=True
    )
    assert os.path.exists(os.path.join(str(art1), "agent_definition.json"))
    assert os.path.exists(os.path.join(str(art1), "final_report.md"))

    # Run 2: Domain 2 (Chemical Safety)
    dir2 = tmp_path / "domain_2_docs"
    dir2.mkdir()
    (dir2 / "chemical_msds.txt").write_text("Chemical Hydrochloric Acid 37%: Wear neoprene gloves and chemical splash goggles.")

    art2 = tmp_path / "domain_2_artifacts"

    res2 = factory.build_agent(
        brief="Assistant for chemical handling safety and personal protective equipment.",
        doc_folder=str(dir2),
        output_dir=str(art2),
        unattended=True
    )
    assert os.path.exists(os.path.join(str(art2), "agent_definition.json"))

    # Verify complete isolation: Run 2 artifacts must not contain Run 1 references
    with open(os.path.join(str(art2), "agent_definition.json")) as f:
        agent_def_2 = json.load(f)
    assert "vessel_log.txt" not in agent_def_2.get("document_references", [])
    assert any("chemical_msds.txt" in ref for ref in agent_def_2.get("document_references", []))
