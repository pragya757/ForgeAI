import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field

class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter]

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.model_dump() for p in self.parameters]
        }

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_definitions(self, allowlist: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        allowed = allowlist if allowlist is not None else list(self._tools.keys())
        return [
            tool.to_dict()
            for name, tool in self._tools.items()
            if name in allowed
        ]

    def execute(self, tool_name: str, allowlist: Optional[List[str]] = None, **kwargs: Any) -> Any:
        if allowlist is not None and tool_name not in allowlist:
            raise PermissionError(
                f"Unauthorized tool execution: Tool '{tool_name}' is not in the agent's authorized allowlist: {allowlist}"
            )
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        return tool.execute(**kwargs)

    def validate_selection(self, selected_tools: List[str]) -> List[str]:
        """Validate that all selected tools exist in registry and filter invalid ones."""
        valid = []
        for t in selected_tools:
            clean = t.strip().lower()
            if clean in self._tools:
                valid.append(clean)
        return valid

# Global tool registry instance
registry = ToolRegistry()
