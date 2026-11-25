import os
import pytest
from app.llm.mock_client import MockLLMClient
from app.runtime.chat_runner import GenericChatRunner

def test_generic_chat_runner_hr():
    runner = GenericChatRunner(
        definition_path="demos/hr_assistant/artifacts/agent_definition.json",
        doc_folder="demos/hr_assistant/documents",
        llm_client=MockLLMClient()
    )
    # 1. Answerable in-scope query
    resp1 = runner.ask("How many days of annual leave do full-time employees get?")
    assert not resp1.refused
    assert "20" in resp1.answer
    assert any("leave_policy.pdf" in c for c in resp1.citations)

    # 2. Unsupported out-of-scope query
    resp2 = runner.ask("Can you tell me what my manager's annual salary and bonus was?")
    assert resp2.refused
    assert "outside my verified" in resp2.answer.lower() or "cannot answer" in resp2.answer.lower()

def test_generic_chat_runner_procurement():
    runner = GenericChatRunner(
        definition_path="demos/procurement_assistant/artifacts/agent_definition.json",
        doc_folder="demos/procurement_assistant/documents",
        llm_client=MockLLMClient()
    )
    # 1. Answerable part search
    resp1 = runner.ask("What is the unit price and available stock for part number NV-PUMP-001?")
    assert not resp1.refused
    assert "4,250" in resp1.answer or "4250" in resp1.answer
    assert len(resp1.tool_calls) >= 1

    # 2. Refusal on payment execution
    resp2 = runner.ask("Please initiate an automated bank wire transfer of $12,400 to supplier Nordik Marine Spares right now.")
    assert resp2.refused
    assert "outside my verified" in resp2.answer.lower() or "cannot answer" in resp2.answer.lower()
