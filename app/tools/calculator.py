import math
import re
from typing import List, Any, Dict
from app.tools.registry import BaseTool, ToolParameter

class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform safe mathematical calculations for pricing, totals, discounts, margins, and quantities."

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="Mathematical expression to evaluate (e.g. '3 * 1800 * 0.95' or '4250 + 950').",
                required=True
            )
        ]

    def execute(self, expression: str, **kwargs: Any) -> Dict[str, Any]:
        clean_expr = str(expression).strip()
        # Clean currency symbols, commas
        clean_expr = clean_expr.replace("$", "").replace(",", "")

        # Strict allowlist of safe mathematical tokens
        if not re.match(r"^[\d\.\s\+\-\*\/\(\)\%]+$", clean_expr):
            return {
                "error": f"Invalid expression. Only digits, operators (+, -, *, /, %), parentheses and decimals are allowed: '{expression}'",
                "result": None
            }

        try:
            # Safe evaluation environment with no builtins
            allowed_names = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
            }
            # Evaluate expression in safe environment
            result = eval(clean_expr, {"__builtins__": None}, allowed_names)
            return {
                "expression": expression,
                "evaluated_expression": clean_expr,
                "result": round(float(result), 4) if isinstance(result, (int, float)) else str(result)
            }
        except Exception as e:
            return {
                "error": f"Evaluation error: {str(e)}",
                "expression": expression,
                "result": None
            }
