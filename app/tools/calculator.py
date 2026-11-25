import ast
import operator
import re
from typing import List, Any, Dict
from app.tools.registry import BaseTool, ToolParameter

class SafeASTEvaluator:
    """Safe mathematical evaluator using AST parsing. Never executes arbitrary Python code."""

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @classmethod
    def evaluate(cls, node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return cls.evaluate(node.body)

        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise ValueError(f"Operator {op_type.__name__} is not permitted.")

            left = cls.evaluate(node.left)
            right = cls.evaluate(node.right)

            # Prevent resource exhaustion via massive exponents
            if op_type is ast.Pow:
                if right > 100 or left > 10000:
                    raise ValueError("Exponent or base exceeds safe mathematical limit.")

            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero.")

            return cls.ALLOWED_OPERATORS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise ValueError(f"Unary operator {op_type.__name__} is not permitted.")
            operand = cls.evaluate(node.operand)
            return cls.ALLOWED_OPERATORS[op_type](operand)

        else:
            raise ValueError(f"Arbitrary code construct '{type(node).__name__}' is strictly prohibited.")

class CalculatorTool(BaseTool):
    """
    Mathematical calculation tool.
    Guarantees:
    - Never evaluates arbitrary Python code
    - Uses strict AST traversal with an operator allowlist
    - Blocks all imports, execution, attributes, and calls
    """

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

        # Quick reject of obviously non-math characters
        if re.search(r"[a-zA-Z_]", clean_expr):
            return {
                "error": f"Security violation: Expression contains prohibited identifiers or code: '{expression}'",
                "result": None
            }

        try:
            # Parse into AST expression mode
            tree = ast.parse(clean_expr, mode="eval")
            result = SafeASTEvaluator.evaluate(tree)

            # Format result
            rounded = round(result, 4)
            if rounded.is_integer():
                rounded = float(int(rounded))

            return {
                "expression": expression,
                "evaluated_expression": clean_expr,
                "result": rounded
            }
        except ZeroDivisionError:
            return {"error": "Division by zero is undefined.", "expression": expression, "result": None}
        except Exception as e:
            return {
                "error": f"Calculation rejected: {str(e)}",
                "expression": expression,
                "result": None
            }
