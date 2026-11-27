import os
import json
import pytest
from pydantic import BaseModel

from app.retrieval.ingestion import IngestionManager
from app.factory.pipeline import ForgeAIFactory
from app.factory.eval_generator import AutomaticEvalGenerator
from app.factory.agent_generator import AgentDefinition
from app.retrieval.document_loader import DocumentLoader

def test_custom_upload_sets_isolated_context_without_demo_leakage(tmp_path):
    """Verify that uploading custom files creates isolated session directories and prevents demo data leakage."""
    pdf_path = "demos/university_regulations/University_Regulations_Test_Document.pdf"
    assert os.path.exists(pdf_path), "Test document must exist"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    ingestion_res = IngestionManager.ingest_files(
        files=[("University_Regulations_Test_Document.pdf", pdf_bytes)],
        base_dir=str(tmp_path / "sessions")
    )

    # 1. Isolated session directories
    assert "session_" in ingestion_res.session_id
    assert os.path.exists(ingestion_res.document_dir)
    assert os.path.exists(ingestion_res.artifacts_dir)
    assert "demos/hr_assistant" not in ingestion_res.document_dir
    assert "demos/hr_assistant" not in ingestion_res.artifacts_dir

    # 2. Manifest integrity
    manifest_file = os.path.join(ingestion_res.document_dir, "corpus_manifest.json")
    assert os.path.exists(manifest_file)
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["session_id"] == ingestion_res.session_id
    assert len(manifest["documents"]) == 1
    assert manifest["documents"][0]["filename"] == "University_Regulations_Test_Document.pdf"

def test_university_regulations_eval_dataset_categories_and_clean_questions():
    """Verify >= 20 relevant test cases covering all required university regulations categories with zero internal filename leakage."""
    generator = AutomaticEvalGenerator()
    doc_folder = "demos/university_regulations"
    docs = DocumentLoader.load_directory(doc_folder)
    assert len(docs) >= 1

    with open("demos/university_regulations/artifacts/agent_definition.json") as f:
        agent_def = AgentDefinition(**json.load(f))

    eval_set, _ = generator.generate_evaluation_set(agent_def, doc_folder, target_count=20)
    assert len(eval_set.cases) >= 20, "Must contain at least 20 test cases"

    # Category coverage validation
    categories = [c.subcategory or c.test_category for c in eval_set.cases]
    questions = [c.question for c in eval_set.cases]

    # Required subtopics:
    # 1. Direct factual
    assert any(c.subcategory == "direct_factual" or "credit hours" in c.question for c in eval_set.cases)
    # 2. Multi-step reasoning
    assert any(c.subcategory == "multi_hop" or "course load" in c.question for c in eval_set.cases)
    # 3. Attendance & examinations
    assert any("examination" in c.question.lower() or "exam" in c.question.lower() for c in eval_set.cases)
    # 4. Grading & academic standing
    assert any("suspension" in c.question.lower() or "probation" in c.question.lower() or "grade" in c.question.lower() for c in eval_set.cases)
    # 5. Graduation & appeals
    assert any("graduation" in c.question.lower() or "petition" in c.question.lower() or "re-evaluation" in c.question.lower() for c in eval_set.cases)
    # 6. Out-of-scope refusals
    assert any(c.expected_action == "refuse" and c.test_category == "out_of_scope" for c in eval_set.cases)
    # 7. Missing-information questions
    assert any(c.expected_action == "refuse" and (c.subcategory == "missing_information" or "study-abroad" in c.question.lower()) for c in eval_set.cases)

    # Question quality validation: zero references to internal filenames
    for c in eval_set.cases:
        assert ".pdf" not in c.question, f"Question contains internal filename reference: '{c.question}'"
        assert ".txt" not in c.question
        assert ".csv" not in c.question
        assert len(c.question.strip()) >= 15
        assert c.expected_action in ["answer", "refuse", "clarify"]
        assert len(c.expected_facts) >= 1

def test_frozen_evaluation_set_invariance_during_optimization(tmp_path):
    """Verify that the evaluation dataset remains strictly frozen during Critic-Optimizer iterations."""
    output_dir = str(tmp_path / "artifacts")
    factory = ForgeAIFactory(max_iterations=2)
    res = factory.build_agent(
        brief="Create an autonomous University Regulations Assistant for academic policies, attendance, grading, and appeals.",
        doc_folder="demos/university_regulations",
        output_dir=output_dir
    )

    eval_set = res["eval_set"]
    scorecards = res["scorecards"]

    assert len(scorecards) >= 1
    frozen_case_ids = [c.test_id for c in eval_set.cases]

    # Check each iteration's scorecard evaluates the exact same set of test IDs
    for sc in scorecards:
        sc_test_ids = [r.test_id for r in sc.case_results]
        assert sc_test_ids == frozen_case_ids, "Test case IDs must not drift between optimization iterations"
        assert sc.total_tests == len(eval_set.cases), "Total test count must remain invariant"

    # Verify pass rate
    final_sc = scorecards[-1]
    assert final_sc.pass_rate >= 0.90, f"Expected >= 90% pass rate, got {final_sc.pass_rate}"
