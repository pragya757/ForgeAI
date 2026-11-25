import os
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ToolParameter(BaseModel):
    name: str
    type: str  # "string", "number", "integer", "boolean"
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

    def validate_arguments(self, **kwargs: Any) -> Dict[str, Any]:
        """Validate input arguments against declared tool parameters."""
        validated = {}
        for param in self.parameters:
            val = kwargs.get(param.name)
            if val is None:
                if param.required:
                    raise ValueError(f"Tool '{self.name}' missing required parameter: '{param.name}'")
                continue

            # Type checking
            if param.type == "string" and not isinstance(val, str):
                val = str(val)
            elif param.type == "integer" and not isinstance(val, int):
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    raise TypeError(f"Tool '{self.name}' parameter '{param.name}' expected integer, got {type(val).__name__}")
            elif param.type == "number" and not isinstance(val, (int, float)):
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    raise TypeError(f"Tool '{self.name}' parameter '{param.name}' expected number, got {type(val).__name__}")
            elif param.type == "boolean" and not isinstance(val, bool):
                if str(val).lower() in ["true", "1", "yes"]:
                    val = True
                elif str(val).lower() in ["false", "0", "no"]:
                    val = False
                else:
                    raise TypeError(f"Tool '{self.name}' parameter '{param.name}' expected boolean, got {type(val).__name__}")

            validated[param.name] = val

        # Pass through any extra kwargs that are not in parameters (e.g. security context)
        for k, v in kwargs.items():
            if k not in validated:
                validated[k] = v

        return validated

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.model_dump() for p in self.parameters]
        }

def sanitize_sensitive_data(obj: Any) -> Any:
    """Recursively mask sensitive keys, tokens, or credential strings."""
    SENSITIVE_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|auth|credential)")
    ]
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            if any(p.search(str(k)) for p in SENSITIVE_PATTERNS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_sensitive_data(item) for item in obj]
    elif isinstance(obj, str):
        # Mask embedded API keys or tokens in strings
        masked = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)['\"]?([A-Za-z0-9_\-]{8,})['\"]?", r"\1[REDACTED]", obj)
        masked = re.sub(r"(?i)(bearer\s+)([A-Za-z0-9_\-\.]{12,})", r"\1[REDACTED]", masked)
        return masked
    return obj

class ToolRegistry:
    """Central registry and security enforcement engine for authorized agent tools."""

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
        """
        Execute tool with strict security guarantees:
        1. Strict tool allowlisting (blocks unapproved tools)
        2. Rejects unregistered tools
        3. Validates tool arguments
        4. Sanitizes output to prevent sensitive data leakage
        """
        # 1. Enforce allowlist
        if allowlist is not None and tool_name not in allowlist:
            raise PermissionError(
                f"Unauthorized tool execution: Tool '{tool_name}' is not in the agent's authorized allowlist: {allowlist}"
            )

        # 2. Prevent unregistered tool execution
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")

        # 3. Validate tool arguments
        validated_args = tool.validate_arguments(**kwargs)

        # 4. Execute tool
        raw_result = tool.execute(**validated_args)

        # 5. Sanitize sensitive outputs
        return sanitize_sensitive_data(raw_result)

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
