"""Demonstration script calling LangChain tools directly without an LLM.

Step 6 Verification:
Ensures each tool is correctly registered with LangChain's @tool decorator,
has an accessible schema/description, and can be invoked directly.
"""

import sys
from tools import calculator_tool, search_tool

# Ensure standard UTF-8 output encoding for console displays
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    print("=" * 60)
    print("STEP 6 VERIFICATION: DIRECT LANGCHAIN TOOL INVOCATION")
    print("=" * 60)

    # 1. Inspect Calculator Tool
    print("\n[1] Testing Calculator Tool (@tool calculator_tool)...")
    print(f"    Name:        {calculator_tool.name}")
    print(f"    Description: {calculator_tool.description.strip().splitlines()[0]}")
    calc_input = {"expression": "(150 - 120) / 120 * 100"}
    calc_result = calculator_tool.invoke(calc_input)
    print(f"    Input:       {calc_input}")
    print(f"    Output:      {calc_result}")
    assert calc_result == "25", f"Expected '25', got '{calc_result}'"
    print("    --> Calculator Tool invocation successful!")

    # 2. Inspect Search Tool
    print("\n[2] Testing Search Tool (@tool search_tool)...")
    print(f"    Name:        {search_tool.name}")
    print(f"    Description: {search_tool.description.strip().splitlines()[0]}")
    search_input = {"query": "Bangladesh population estimate"}
    search_result = search_tool.invoke(search_input)
    print(f"    Input:       {search_input}")
    # Print a truncated preview of the observation
    preview = search_result[:300] + ("..." if len(search_result) > 300 else "")
    print(f"    Output Preview:\n{preview}")
    assert "URL:" in search_result, "Expected 'URL:' in search results"
    print("    --> Search Tool invocation successful!")

    print("\n" + "=" * 60)
    print("ALL TOOLS SUCCESSFULLY TESTED DIRECTLY (ZERO LLM DEPENDENCY)")
    print("=" * 60)


if __name__ == "__main__":
    main()
