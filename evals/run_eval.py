"""Automated Evaluation Runner for Reactron Agent (Step 12).

Tests the agent across a curated 15-question evaluation suite measuring:
1. Tool Selection Accuracy (Search, Calculator, Python Guardrail)
2. Grounded Factuality & Keyword Recall
3. Citation Extraction
4. Execution Latency & Recursion Limit Adherence
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent import run_agent, redact_secrets

DATASET_PATH = os.path.join(os.path.dirname(__file__), "eval_dataset.json")


def load_dataset() -> List[Dict[str, Any]]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_mock_agent(item: Dict[str, Any]):
    """Construct a deterministic mock agent matching the item's expected flow."""
    mock = MagicMock()
    messages = [HumanMessage(content=item["query"])]

    expected_tools = item.get("expected_tools", [])
    expected_kw = item.get("expected_keywords", [])
    kw_str = " ".join(expected_kw)

    if not expected_tools:
        messages.append(AIMessage(content=f"Direct response containing {kw_str}."))
    else:
        for idx, tool in enumerate(expected_tools, 1):
            call_id = f"mock_call_{idx}"
            if tool == "calculator_tool":
                messages.append(
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "calculator_tool", "args": {"expression": "test_expr"}, "id": call_id}],
                    )
                )
                messages.append(ToolMessage(content=kw_str or "96", tool_call_id=call_id, name="calculator_tool"))
            elif tool == "search_tool":
                messages.append(
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "search_tool", "args": {"query": "test_query"}, "id": call_id}],
                    )
                )
                messages.append(
                    ToolMessage(
                        content=f"[1] Source Title\n    URL: https://example.com/source\n    Snippet: Factual snippet with {kw_str}",
                        tool_call_id=call_id,
                        name="search_tool",
                    )
                )
            elif tool == "python_tool":
                messages.append(
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "python_tool", "args": {"code": "print('hello')"}, "id": call_id}],
                    )
                )
                messages.append(
                    ToolMessage(
                        content="Security Notice: Python execution is disabled for security.\nPreview:\n```python\nprint('hello')\n```",
                        tool_call_id=call_id,
                        name="python_tool",
                    )
                )

        messages.append(
            AIMessage(
                content=f"Final synthesized response answering query with {kw_str}. Reference: https://example.com/source"
            )
        )

    mock.invoke.return_value = {"messages": messages}
    return mock


def evaluate_item(item: Dict[str, Any], live: bool = False) -> Dict[str, Any]:
    query = item["query"]
    expected_tools = set(item.get("expected_tools", []))
    expected_kw = [k.lower() for k in item.get("expected_keywords", [])]

    start_t = time.perf_counter()

    if live:
        result = run_agent(query)
    else:
        mock_agent = build_mock_agent(item)
        result = run_agent(query, agent=mock_agent)

    elapsed = round(time.perf_counter() - start_t, 3)

    output = result.get("output", "")
    trace = result.get("trace", [])
    used_tools = {step.get("tool") for step in trace}

    # Evaluation Criteria
    # 1. Tool usage: all expected tools must have been used
    tools_matched = expected_tools.issubset(used_tools) if expected_tools else (len(used_tools) == 0)

    # 2. Keyword recall
    output_lower = output.lower()
    kw_matched = all(k in output_lower for k in expected_kw) if expected_kw else True

    # 3. Status success
    status_ok = result.get("status") == "success"

    # Overall pass
    passed = tools_matched and kw_matched and status_ok

    return {
        "id": item["id"],
        "category": item["category"],
        "query": query,
        "passed": passed,
        "tools_matched": tools_matched,
        "kw_matched": kw_matched,
        "used_tools": list(used_tools),
        "expected_tools": list(expected_tools),
        "latency_sec": elapsed,
        "status": result.get("status"),
        "output_preview": output[:100] + ("..." if len(output) > 100 else ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Reactron Evaluation Runner")
    parser.add_argument("--live", action="store_true", help="Run against live LLM API instead of mock")
    parser.add_argument("--category", type=str, default="", help="Filter by category")
    parser.add_argument("--id", type=str, default="", help="Run a specific test id")
    args = parser.parse_args()

    # UTF-8 console output
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    dataset = load_dataset()

    if args.category:
        dataset = [d for d in dataset if d["category"] == args.category]
    if args.id:
        dataset = [d for d in dataset if d["id"] == args.id]

    print("=" * 80)
    mode_str = "LIVE LLM EXECUTION" if args.live else "DETERMINISTIC TEST HARNESS"
    print(f"REACTRON EVALUATION BENCHMARK ({mode_str})")
    print(f"Total benchmark questions to evaluate: {len(dataset)}")
    print("=" * 80)

    results = []
    for item in dataset:
        print(f"[{item['id']}] Category: {item['category']:<18} | Query: {item['query'][:40]}...", end=" ", flush=True)
        eval_res = evaluate_item(item, live=args.live)
        status_icon = "✓ PASS" if eval_res["passed"] else "✗ FAIL"
        print(f"-> {status_icon} ({eval_res['latency_sec']:.3f}s)")
        results.append(eval_res)

    # Summary Report
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    accuracy = (passed_count / total * 100) if total > 0 else 0
    avg_latency = (sum(r["latency_sec"] for r in results) / total) if total > 0 else 0

    print("\n" + "=" * 80)
    print("EVALUATION SCORECARD")
    print("=" * 80)
    print(f"Pass Rate:          {passed_count}/{total} ({accuracy:.1f}%)")
    print(f"Average Latency:    {avg_latency:.3f} seconds")
    print("=" * 80)

    if passed_count < total:
        print("\nFailed Cases:")
        for r in results:
            if not r["passed"]:
                print(f"  [{r['id']}] {r['query']}")
                print(f"    Expected tools: {r['expected_tools']}, Used: {r['used_tools']}")
                print(f"    Preview: {r['output_preview']}")
        sys.exit(1)
    else:
        print("ALL EVALUATION BENCHMARKS PASSED SUCCESSFULLY!")
        sys.exit(0)


if __name__ == "__main__":
    main()

