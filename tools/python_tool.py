import ast
from langchain_core.tools import tool

MAX_CODE_LENGTH = 2000


def run_python_code(code: str) -> str:
    """Safely inspect and preview Python code without executing it.

    Args:
        code: The Python code snippet to review.

    Returns:
        A structured safety notice including code preview and syntax verification,
        without executing the code.
    """
    if not isinstance(code, str):
        return "Error: Code snippet must be a string."

    clean_code = code.strip()
    if not clean_code:
        return "Error: Code snippet cannot be empty."

    if len(clean_code) > MAX_CODE_LENGTH:
        return f"Error: Code exceeds maximum allowed length of {MAX_CODE_LENGTH} characters."

    # Validate Python syntax without executing
    try:
        ast.parse(clean_code)
        syntax_status = "Syntax Valid"
    except SyntaxError as e:
        syntax_status = f"Syntax Error: {e.msg} at line {e.lineno}"

    return (
        "Security Notice: Python execution is disabled in this version for security. "
        "I can explain the code or provide a safe, non-executed preview, but direct execution is blocked.\n\n"
        f"Status: {syntax_status}\n"
        "Preview:\n"
        "```python\n"
        f"{clean_code}\n"
        "```"
    )


@tool
def python_tool(code: str) -> str:
    """Preview Python code safely without executing it.

    Use this tool when Python code inspection, formatting, or syntax review is
    needed. Arbitrary code execution is disabled by default for system security.

    Args:
        code: Python code snippet string to inspect.
    """
    return run_python_code(code)

