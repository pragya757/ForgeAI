import os
import pytest
import pandas as pd
from app.tools.registry import registry, BaseTool, ToolParameter
from app.tools.calculator import CalculatorTool
from app.tools.csv_lookup import CSVLookupTool
from app.tools.current_date import CurrentDateTool
from app.tools.weather import WeatherTool

def test_tool_registry_discovery():
    tools = registry.list_tools()
    assert "csv_lookup" in tools
    assert "calculator" in tools
    assert "weather" in tools
    assert "current_date" in tools

def test_calculator_execution():
    calc = CalculatorTool()
    res1 = calc.execute(expression="3 * 1800 * 0.95")
    assert res1["result"] == 5130.0

    res2 = calc.execute(expression="4250 + 950")
    assert res2["result"] == 5200.0

    # Malicious expression block
    res_bad = calc.execute(expression="__import__('os').system('ls')")
    assert "error" in res_bad
    assert res_bad["result"] is None

def test_csv_lookup_execution(tmp_path):
    csv_file = tmp_path / "spares.csv"
    df = pd.DataFrame([
        {"part_no": "NV-001", "name": "Fuel Pump", "price": 4250, "stock": 4},
        {"part_no": "TB-882", "name": "Bearing", "price": 3100, "stock": 2}
    ])
    df.to_csv(str(csv_file), index=False)

    csv_tool = CSVLookupTool()
    res = csv_tool.execute(file_path=str(csv_file), query="NV-001")
    assert res["total_matches"] == 1
    assert res["results"][0]["name"] == "Fuel Pump"
    assert res["results"][0]["price"] == 4250

def test_current_date_tool():
    date_tool = CurrentDateTool()
    res = date_tool.execute()
    assert "date" in res
    assert "iso_timestamp" in res
    assert "weekday" in res

def test_tool_allowlist_enforcement():
    allowlist = ["calculator", "current_date"]

    # Allowed execution
    res = registry.execute("calculator", allowlist=allowlist, expression="10 + 5")
    assert res["result"] == 15.0

    # Unauthorized tool blocked by PermissionError
    with pytest.raises(PermissionError):
        registry.execute("csv_lookup", allowlist=allowlist, file_path="none.csv")
