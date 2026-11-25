from app.tools.registry import BaseTool, ToolRegistry, registry
from app.tools.csv_lookup import CSVLookupTool
from app.tools.calculator import CalculatorTool
from app.tools.weather import WeatherTool
from app.tools.current_date import CurrentDateTool

# Register all default tools into global registry
registry.register(CSVLookupTool())
registry.register(CalculatorTool())
registry.register(WeatherTool())
registry.register(CurrentDateTool())

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "registry",
    "CSVLookupTool",
    "CalculatorTool",
    "WeatherTool",
    "CurrentDateTool"
]
