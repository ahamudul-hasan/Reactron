"""Reactron ReAct Agent Orchestration Module.

This module builds and invokes the LangChain/LangGraph ReAct agent, coordinating
the chat model, external tools (Search, Calculator, Safe Python), and trace capture.
"""

import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from tools import calculator_tool, python_tool, search_tool

# Load local environment variables from .env
load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]

SYSTEM_PROMPT = """You are Reactron, an expert analytical AI assistant that solves multi-step problems using reasoning and tools.

Follow these strict operational rules:
1. Use 'calculator_tool' for any and all mathematical computations, percentages, or numeric evaluations. Never compute arithmetic in your head.
2. Use 'search_tool' to retrieve live facts, demographic statistics, or external information. Always extract precise numbers from the search results.
3. Use 'python_tool' only if code review, explanation, or syntax inspection is specifically requested. Python execution is disabled for security.
4. When you answer, cite the sources or URLs provided in the search observations.
5. Provide a direct, concise, and grounded final answer based strictly on tool observations.
"""


def get_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Initialize the chat model provider.

    Args:
        model_name: Name of the Gemini model (defaults to GEMINI_MODEL or gemini-3.5-flash).
        temperature: Model sampling temperature (0 for deterministic tool invocation).

    Returns:
        ChatGoogleGenerativeAI instance.

    Raises:
        ValueError: If GOOGLE_API_KEY is not set.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing Google Gemini API key. Please set GOOGLE_API_KEY in your .env file."
        )

    selected_model = model_name or DEFAULT_MODEL
    return ChatGoogleGenerativeAI(
        model=selected_model,
        temperature=temperature,
        google_api_key=api_key,
    )


def build_agent(llm: Optional[ChatGoogleGenerativeAI] = None, tools: Optional[List[Any]] = None):
    """Construct a LangChain ReAct agent with tools and system prompt.

    Args:
        llm: Chat model instance (creates default if None).
        tools: List of tools (defaults to calculator_tool, search_tool, python_tool).

    Returns:
        Compiled agent runnable.
    """
    model = llm or get_llm()
    agent_tools = tools or [search_tool, calculator_tool, python_tool]
    return create_agent(model=model, tools=agent_tools, system_prompt=SYSTEM_PROMPT)


def _extract_text_content(content: Any) -> str:
    """Extract plain text from string or structured content lists."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def run_agent(query: str, agent=None) -> Dict[str, Any]:
    """Execute the agent on a user query and return the answer, trace, and citations.

    Args:
        query: User prompt or question string.
        agent: Optional pre-compiled agent runnable.

    Returns:
        Dict containing:
            - output: Final text response
            - trace: List of tool execution events (tool, input, output, status)
            - sources: Deduplicated list of source URLs discovered during search
            - status: "success" or "error"
    """
    if not isinstance(query, str) or not query.strip():
        return {
            "output": "Error: Query cannot be empty.",
            "trace": [],
            "sources": [],
            "status": "error",
        }

    clean_query = query.strip()

    try:
        active_agent = agent or build_agent()
    except Exception as e:
        return {
            "output": f"Configuration Error: {e}",
            "trace": [],
            "sources": [],
            "status": "error",
        }

    try:
        response = active_agent.invoke({"messages": [{"role": "user", "content": clean_query}]})
    except Exception as e:
        return {
            "output": f"Execution Error: {e}",
            "trace": [],
            "sources": [],
            "status": "error",
        }

    messages = response.get("messages", [])
    tool_calls_map: Dict[str, Dict[str, Any]] = {}
    trace: List[Dict[str, Any]] = []
    sources: List[str] = []
    final_answer = ""

    # Parse execution trace and final output
    for msg in messages:
        msg_type = msg.__class__.__name__

        if msg_type == "AIMessage":
            # Check for tool call requests
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    tc_id = tc.get("id")
                    if tc_id:
                        tool_calls_map[tc_id] = {
                            "tool": tc.get("name", "unknown_tool"),
                            "input": tc.get("args", {}),
                        }
            else:
                # AIMessage without tool calls represents synthesis/final answer
                final_answer = _extract_text_content(msg.content)

        elif msg_type == "ToolMessage":
            tc_id = getattr(msg, "tool_call_id", None)
            tc_info = tool_calls_map.get(tc_id, {})
            tool_name = getattr(msg, "name", None) or tc_info.get("tool", "tool")
            tool_input = tc_info.get("input", {})
            raw_output = _extract_text_content(msg.content)

            # Determine execution status
            is_err = "error" in raw_output.lower() and not raw_output.startswith("Security Notice")
            trace_status = "error" if is_err else "success"

            trace.append({
                "tool": tool_name,
                "input": tool_input,
                "output": raw_output,
                "status": trace_status,
            })

            # Extract URLs from tool outputs
            found_urls = re.findall(r"https?://[^\s<>\"'\]]+", raw_output)
            for url in found_urls:
                clean_url = url.rstrip(".,;)")
                if clean_url not in sources:
                    sources.append(clean_url)

    if not final_answer and messages:
        final_answer = _extract_text_content(messages[-1].content)

    return {
        "output": final_answer or "No response generated.",
        "trace": trace,
        "sources": sources,
        "status": "success",
    }


def main():
    """Command-line entrypoint to run the agent."""
    import sys

    # Set UTF-8 encoding for console output
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 65)
    print("REACTRON AGENT: COMMAND-LINE RUNNER (STEP 8)")
    print("=" * 65)

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = (
            "Search for the latest population estimate for Bangladesh "
            "and calculate 5% of that number."
        )

    print(f"\nUser Query: {query}\n")
    print("Running agent thinking & acting loop...")

    result = run_agent(query)

    print("\n" + "-" * 40 + " AGENT TRACE " + "-" * 40)
    for i, step in enumerate(result["trace"], 1):
        print(f"\n[Step {i}] Tool: {step['tool']} ({step['status']})")
        print(f"  Input:  {step['input']}")
        preview = step["output"][:200] + ("..." if len(step["output"]) > 200 else "")
        print(f"  Output: {preview}")

    print("\n" + "=" * 40 + " FINAL ANSWER " + "=" * 40)
    print(result["output"])

    if result["sources"]:
        print("\n" + "-" * 40 + " CITATIONS " + "-" * 40)
        for src in result["sources"]:
            print(f"- {src}")
    print("=" * 65)


if __name__ == "__main__":
    main()
