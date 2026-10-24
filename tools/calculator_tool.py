"""Calculator tool using numexpr for safe arithmetic evaluation.

This tool safely parses and calculates mathematical expressions without using
Python's built-in `eval()`. It validates input character sets, restricts
namespaces, enforces length bounds, and checks parentheses balance.
"""

import math
import re
from langchain_core.tools import tool
import numexpr as ne

# Maximum allowed character length for an expression
MAX_EXPRESSION_LENGTH = 200

# Permitted character set: digits, basic arithmetic operators, parentheses, dot, space, percent, caret
ALLOWED_CHARACTERS_REGEX = re.compile(r"^[0-9+\-*/().\s%^]+$")


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely using numexpr.

    Args:
        expression: A string containing numeric arithmetic (e.g., '12 * 8',
                    '(150 - 120) / 120 * 100', or '5 / 100 * 170000000').

    Returns:
        A formatted string of the calculation result or a descriptive error message.
    """
    if not isinstance(expression, str):
        return "Error: Expression must be a string."

    expr = expression.strip()
    if not expr:
        return "Error: Expression cannot be empty."

    if len(expr) > MAX_EXPRESSION_LENGTH:
        return f"Error: Expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters."

    # Remove thousands separators between digits (e.g., 170,000,000 -> 170000000)
    expr = re.sub(r"(?<=\d),(?=\d)", "", expr)

    # Convert '^' (common LLM notation for exponentiation) to '**'
    expr = expr.replace("^", "**")

    # Convert percentage notation (e.g., '5%' -> '(5 / 100)') when not used as modulo
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%(?!\s*\d)", r"(\1 / 100)", expr)

    # Check for disallowed characters (variables, letters, builtins)
    if not ALLOWED_CHARACTERS_REGEX.match(expr):
        return (
            "Error: Invalid characters in expression. "
            "Only numbers and basic arithmetic operators (+, -, *, /, %, **) are allowed."
        )

    # Verify balanced parentheses
    depth = 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return "Error: Unbalanced parentheses in expression."
    if depth != 0:
        return "Error: Unbalanced parentheses in expression."

    try:
        # Evaluate with completely isolated namespaces
        raw_result = ne.evaluate(expr, local_dict={}, global_dict={})
        val = raw_result.item() if hasattr(raw_result, "item") else raw_result

        if isinstance(val, (int, float)):
            if math.isinf(val):
                return "Error: Calculation resulted in infinity."
            if math.isnan(val):
                return "Error: Calculation resulted in an undefined value (NaN)."
            # Format clean integers (e.g. 25.0 -> 25)
            if isinstance(val, float) and val.is_integer():
                val = int(val)

        return str(val)
    except ZeroDivisionError:
        return "Error: Division by zero."
    except KeyError as e:
        return f"Error: Unsupported variable or identifier {e}."
    except SyntaxError:
        return "Error: Malformed mathematical expression."
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool
def calculator_tool(expression: str) -> str:
    """Calculate the result of a mathematical expression.

    Use this tool whenever you need to compute numbers, percentages, or
    arithmetic expressions. Do not calculate math in your head.

    Args:
        expression: Mathematical expression to evaluate (e.g., '12 * 8',
                    '(150 - 120) / 120 * 100', '5 / 100 * 170000000').
    """
    return calculate(expression)
