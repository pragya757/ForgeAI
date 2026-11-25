import os
import pytest
import pandas as pd
from app.llm.mock_client import MockLLMClient
from app.factory.pipeline import ForgeAIFactory

def test_unseen_domain_pipeline(tmp_path):
    """
    Test that ForgeAI works completely generic on an unseen brief
    and document collection without modifying any source code.
    Domain: IT Equipment & Cybersecurity Asset Management.
    """
    doc_dir = tmp_path / "unseen_docs"
    out_dir = tmp_path / "unseen_artifacts"
    doc_dir.mkdir()
    out_dir.mkdir()

    # Create unseen domain documents
    it_policy = doc_dir / "it_security_policy.txt"
    it_policy.write_text(
        "IT SECURITY ASSET MANAGEMENT POLICY:\n"
        "1. Standard laptop refresh cycle is thirty-six (36) months for engineering staff.\n"
        "2. Multi-factor authentication (MFA) via hardware security key is mandatory for production access.\n"
        "3. Lost or stolen laptops must be reported to security@company.com within two (2) hours of discovery.\n"
        "4. Unauthorized software installation on corporate assets constitutes a Class 1 security violation.\n",
        encoding="utf-8"
    )

    unseen_brief = (
        "Create an IT Security Assistant that helps employees understand hardware refresh cycles, "
        "MFA compliance, lost device protocols, and software installation restrictions using IT policies."
    )

    factory = ForgeAIFactory(llm_client=MockLLMClient(), max_iterations=2)
    results = factory.build_agent(
        brief=unseen_brief,
        doc_folder=str(doc_dir),
        output_dir=str(out_dir),
        unattended=True
    )

    # Verify all 7 mandatory artifacts were produced
    assert os.path.exists(out_dir / "requirements.json")
    assert os.path.exists(out_dir / "groundability_report.json")
    assert os.path.exists(out_dir / "agent_definition.json")
    assert os.path.exists(out_dir / "eval_set.json")
    assert os.path.exists(out_dir / "eval_generation_prompt.txt")
    assert os.path.exists(out_dir / "scorecards.json")
    assert os.path.exists(out_dir / "iteration_logs.json")
    assert os.path.exists(out_dir / "final_report.md")

    # Verify >= 20 evaluation cases generated
    eval_set = results["eval_set"]
    assert len(eval_set.cases) >= 20

    # Verify final report was generated
    assert len(results["report_md"]) > 200
