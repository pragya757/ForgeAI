from datetime import datetime, timezone
from typing import List, Any, Dict
from app.tools.registry import BaseTool, ToolParameter

class CurrentDateTool(BaseTool):
    @property
    def name(self) -> str:
        return "current_date"

    @property
    def description(self) -> str:
        return "Returns current date, time, weekday, and ISO timestamp for time-sensitive policy or delivery checks."

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        now = datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "year": now.year,
            "month": now.strftime("%B"),
            "iso_timestamp": now.isoformat()
        }
