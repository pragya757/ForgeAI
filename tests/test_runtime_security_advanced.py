import os
import json
import pytest
from unittest.mock import patch
import requests

from app.llm.mock_client import MockLLMClient
from app.runtime.chat_runner import GenericChatRunner, ChatResponse
from app.schemas.agent_definition import (
    AgentDefinition,
    OutputContract,
    CitationRequirements,
    ModelConfig
)
from app.tools.registry import registry, sanitize_sensitive_data
from app.tools.calculator import CalculatorTool
from app.tools.csv_lookup import CSVLookupTool
from app.tools.weather import WeatherTool

@pytest.fixture
def mock_llm():
    return MockLLMClient()

@pytest.fixture
def base_definition():
    return AgentDefinition(
        agent_name="Fleet Procurement Assistant",
        description="Assists with technical parts procurement.",
        system_prompt="Answer procurement inquiries strictly from technical manuals.",
        target_audience="Procurement Officers",
        supported_topics=["Spare parts pricing", "Part numbers", "Stock levels"],
        unsupported_topics=["Employee salaries", "Wire transfers"],
        must_refuse_topics=["Employee salaries", "Wire transfers"],
        document_references=["spare_parts_catalog.csv"],
        chunk_size=400,
        chunk_overlap=80,
        top_k=3,
        similarity_threshold=0.35,
        output_contract=OutputContract(format="markdown"),
        citation_requirements=CitationRequirements(mandatory=True, tag_format="[Source: <filename>]"),
        tool_selection=["csv_lookup"],
        tool_justifications={"csv_lookup": "Required for spare part stock lookups."},
        refusal_policy="Strict",
        model_config=ModelConfig()
    )

# 1. Test Dynamic Configuration Loading
def test_dynamic_configuration_loading_modes(tmp_path, base_definition, mock_llm):
    # Mode A: Load from AgentDefinition instance
    runner_obj = GenericChatRunner(
        definition=base_definition,
        doc_folder="demos/procurement_assistant/documents",
        llm_client=mock_llm
    )
    assert runner_obj.definition.agent_name == "Fleet Procurement Assistant"

    # Mode B: Load from Python dictionary
    raw_dict = base_definition.model_dump()
    runner_dict = GenericChatRunner(
        definition=raw_dict,
        doc_folder="demos/procurement_assistant/documents",
        llm_client=mock_llm
    )
    assert runner_dict.definition.agent_name == "Fleet Procurement Assistant"

    # Mode C: Load from JSON file path
    json_path = tmp_path / "agent_def.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(base_definition.model_dump_json(indent=2))

    runner_file = GenericChatRunner(
        definition_path=str(json_path),
        doc_folder="demos/procurement_assistant/documents",
        llm_client=mock_llm
    )
    assert runner_file.definition.agent_name == "Fleet Procurement Assistant"

# 2. Test Multi-Turn Conversation History
def test_conversation_history_retention_and_reset(base_definition, mock_llm):
    runner = GenericChatRunner(
        definition=base_definition,
        doc_folder="demos/procurement_assistant/documents",
        llm_client=mock_llm
    )

    # First turn
    resp1 = runner.ask("What is the unit price of NV-PUMP-001?")
    assert not resp1.refused
    assert len(runner.history) == 2  # 1 user + 1 assistant
    assert resp1.history_length == 2

    # Second turn
    resp2 = runner.ask("How many units are in the Rotterdam depot?")
    assert not resp2.refused
    assert len(runner.history) == 4  # 2 user + 2 assistant
    assert resp2.history_length == 4

    # History Reset
    runner.reset_history()
    assert len(runner.history) == 0

# 3. Test Strict Tool Allowlisting & Access Prevention
def test_agent_cannot_access_unauthorized_tool(base_definition, mock_llm):
    # Agent definition only authorizes "current_date"
    limited_def = base_definition.model_copy(deep=True)
    limited_def.tool_selection = ["current_date"]

    runner = GenericChatRunner(
        definition=limited_def,
        doc_folder="demos/procurement_assistant/documents",
        llm_client=mock_llm
    )

    # Date tool is authorized and executes
    date_calls = runner.run_tools_if_needed("What is today's date?")
    assert any(c["tool"] == "current_date" for c in date_calls)

    # Calculator is NOT in tool_selection -> must not be invoked
    calc_calls = runner.run_tools_if_needed("Calculate 4250 * 3")
    assert not any(c["tool"] == "calculator" for c in calc_calls)

    # Direct execution of unapproved tool through registry raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        registry.execute("csv_lookup", allowlist=limited_def.tool_selection, file_path="spare_parts.csv")
    assert "Unauthorized tool execution" in str(exc_info.value)

# 4. Test Prevention of Unregistered Tools
def test_unregistered_tool_rejection():
    with pytest.raises(ValueError) as exc_info:
        registry.execute("arbitrary_unknown_tool")
    assert "not found in registry" in str(exc_info.value)

# 5. Test Tool Argument Validation
def test_tool_argument_validation():
    calc = CalculatorTool()

    # Missing required argument raises ValueError
    with pytest.raises(ValueError) as exc_info:
        calc.validate_arguments()
    assert "missing required parameter" in str(exc_info.value)

    # Invalid type raises TypeError
    with pytest.raises(TypeError) as exc_info:
        registry.execute("weather", allowlist=["weather"], latitude="invalid_lat", longitude=10.0)
    assert "expected number" in str(exc_info.value)

# 6. Test Never Execute Arbitrary Python Code
def test_calculator_blocks_arbitrary_python_code():
    calc = CalculatorTool()

    # Legitimate math passes
    res_valid = calc.execute("4250 + (950 * 2)")
    assert res_valid["result"] == 6150.0

    # Malicious code attempts are strictly blocked
    dangerous_payloads = [
        "__import__('os').system('ls')",
        "eval('2 + 2')",
        "open('/etc/passwd').read()",
        "import os",
        "lambda x: x + 1",
        "subprocess.run(['echo', 'hacked'])",
        "__builtins__",
        "os.popen('whoami').read()"
    ]
    for payload in dangerous_payloads:
        res = calc.execute(payload)
        assert res["result"] is None
        assert "error" in res
        assert ("Security violation" in res["error"] or "Calculation rejected" in res["error"])

    # Exponent resource exhaustion is bounded
    res_exp = calc.execute("2 ** 99999999999")
    assert res_exp["result"] is None
    assert "error" in res_exp

# 7. Test External API Timeout and Error Handling
def test_weather_tool_timeout_and_error_handling():
    weather = WeatherTool()

    # Test network timeout handling
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        res = weather.execute(latitude=51.5, longitude=-0.12)
        assert res["status"] == "timeout"
        assert "timed out" in res["error"]
        assert "temperature_celsius" in res  # Offline fallback returned

    # Test network connection failure handling
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("DNS failure")):
        res2 = weather.execute(latitude=51.5, longitude=-0.12)
        assert res2["status"] == "network_error"
        assert "temperature_celsius" in res2

# 8. Test Restrict CSV Lookup to Authorized Input Files
def test_csv_lookup_security_and_path_traversal(tmp_path):
    safe_dir = tmp_path / "docs"
    safe_dir.mkdir()
    safe_csv = safe_dir / "catalog.csv"
    safe_csv.write_text("item,price\npump,4250\n", encoding="utf-8")

    csv_tool = CSVLookupTool()

    # 1. Allowed lookup inside authorized directory
    res = csv_tool.execute(
        file_path=str(safe_csv),
        query="pump",
        authorized_directory=str(safe_dir),
        authorized_files=["catalog.csv"]
    )
    assert res["total_matches"] == 1

    # 2. Block path traversal
    with pytest.raises(PermissionError) as exc_info:
        csv_tool.execute(file_path="../../etc/passwd", authorized_directory=str(safe_dir))
    assert "Security violation" in str(exc_info.value)

    # 3. Block non-CSV file extensions
    secret_file = safe_dir / "passwords.txt"
    secret_file.write_text("secret_password", encoding="utf-8")
    with pytest.raises(PermissionError) as exc_info:
        csv_tool.execute(file_path=str(secret_file), authorized_directory=str(safe_dir))
    assert "strictly restricted to .csv files" in str(exc_info.value)

    # 4. Block files outside authorized directory
    external_csv = tmp_path / "outside.csv"
    external_csv.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(PermissionError) as exc_info:
        csv_tool.execute(file_path=str(external_csv), authorized_directory=str(safe_dir))
    assert "outside authorized directory" in str(exc_info.value)

# 9. Test Sensitive Configuration Masking
def test_sensitive_configuration_sanitization():
    sensitive_dict = {
        "api_key": "ollama_secret_token_12345",
        "agent_name": "Procurement Agent",
        "nested": {
            "password": "super_secret_password",
            "normal_field": "public_data"
        }
    }
    cleaned = sanitize_sensitive_data(sensitive_dict)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert cleaned["nested"]["normal_field"] == "public_data"
    assert cleaned["agent_name"] == "Procurement Agent"

# 10. Test Both HR and Procurement Agents on Same Generic Runtime
def test_same_generic_runtime_runs_both_hr_and_procurement(mock_llm):
    # Run HR Assistant
    hr_runner = GenericChatRunner(
        definition_path="demos/hr_assistant/artifacts/agent_definition.json",
        doc_folder="demos/hr_assistant/documents",
        llm_client=mock_llm
    )
    assert hr_runner.definition.agent_name == "HR Policy Assistant"
    # HR agent only has date tool, cannot execute csv_lookup
    assert "csv_lookup" not in hr_runner.definition.tool_selection

    hr_resp = hr_runner.ask("How many days of annual leave do full-time employees get?")
    assert not hr_resp.refused
    assert "20" in hr_resp.answer
    assert any("leave_policy.pdf" in c for c in hr_resp.citations)

    # Run Procurement Assistant using the EXACT SAME GenericChatRunner class
    proc_runner = GenericChatRunner(
        definition_path="demos/procurement_assistant/artifacts/agent_definition.json",
        doc_folder="demos/procurement_assistant/documents",
        llm_client=mock_llm
    )
    assert proc_runner.definition.agent_name == "Ship-Spares Procurement Assistant"
    assert "csv_lookup" in proc_runner.definition.tool_selection

    proc_resp = proc_runner.ask("What is the unit price and available stock for part number NV-PUMP-001?")
    assert not proc_resp.refused
    assert "4,250" in proc_resp.answer or "4250" in proc_resp.answer
    assert len(proc_resp.tool_calls) >= 1
