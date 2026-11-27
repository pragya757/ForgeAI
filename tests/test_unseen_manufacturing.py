import os
import json
import pytest
from app.factory.pipeline import ForgeAIFactory
from app.retrieval.ingestion import IngestionManager
from app.runtime.chat_runner import GenericChatRunner
from app.schemas.agent_definition import AgentDefinition

def test_manufacturing_operations_workflow_and_isolation():
    brief = (
        "Create a Manufacturing Operations Assistant that helps plant engineers and technicians "
        "understand standard operating procedures, machine maintenance intervals, quality inspection "
        "criteria, safety lockouts, spare parts procurement, and shift handover protocols. The assistant "
        "must answer using only the uploaded manufacturing operations document, provide accurate source "
        "citations, and clearly refuse or acknowledge missing information when a question cannot be answered from the document."
    )
    doc_path = "tests/fixtures/Manufacturing_Operations_Test_Document.pdf"
    assert os.path.exists(doc_path), f"Fixture not found: {doc_path}"

    with open(doc_path, "rb") as f:
        pdf_bytes = f.read()

    im = IngestionManager()
    session_id = "test_pytest_manufacturing_session"
    res = im.ingest_files(
        files=[("Manufacturing_Operations_Test_Document.pdf", pdf_bytes)],
        session_id=session_id
    )

    factory = ForgeAIFactory(max_iterations=3)
    results = factory.build_agent(
        brief=brief,
        doc_folder=res.document_dir,
        output_dir=res.artifacts_dir,
        unattended=True
    )

    req = results["requirements"]
    assert req.agent_name == "Manufacturing Operations Assistant"
    assert "Manufacturing" in req.domain
    assert "HR" not in req.domain and "University" not in req.domain

    assert len(results["eval_set"].cases) >= 20
    assert len(results["scorecards"]) <= 3
    assert results["scorecards"][-1].pass_rate >= 0.90

    # Test runtime chat runner
    runner = GenericChatRunner(
        definition=results["agent_definition"],
        doc_folder=res.document_dir
    )

    # 1. Answerable query (Meridian Components authentic manual)
    q_ans = "What is the scheduled interval for preventive maintenance on plant machinery?"
    resp_ans = runner.ask(q_ans)
    assert not resp_ans.refused
    assert "500" in resp_ans.answer or "90" in resp_ans.answer
    assert any("Manufacturing_Operations_Test_Document.pdf" in c for c in resp_ans.citations)

    # 2. Scope boundary refusal
    q_ref = "Can you approve 8 hours of overtime pay on the shift supervisor payroll sheet?"
    resp_ref = runner.ask(q_ref)
    assert resp_ref.refused or "cannot answer" in resp_ref.answer.lower()
