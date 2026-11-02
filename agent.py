"""Reactron ReAct Agent Orchestration Module.

This module builds and invokes the LangChain/LangGraph ReAct agent, coordinating
the chat model, external tools (Search, Calculator, Safe Python), and trace capture.
"""

import os
import re
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.errors import GraphRecursionError

from tools import calculator_tool, python_tool, search_tool

# Load local environment variables from .env
load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
DEFAULT_MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "8"))
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]


def redact_secrets(text: str) -> str:
    """Mask sensitive tokens, API keys, and credentials from output strings."""
    if not isinstance(text, str):
        return text
    # Tavily keys: tvly-...
    redacted = re.sub(r"tvly-[A-Za-z0-9_-]{8,}", "[REDACTED_TAVILY_KEY]", text)
    # Google keys: AIzaSy...
    redacted = re.sub(r"AIzaSy[A-Za-z0-9_-]{25,}", "[REDACTED_GOOGLE_KEY]", redacted)
    # Generic tokens: sk-...
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_API_KEY]", redacted)
    return redacted

SYSTEM_PROMPT = """You are Reactron, an expert analytical AI assistant that solves multi-step problems using reasoning and tools.

Follow these strict operational rules:
1. Use 'calculator_tool' for any and all mathematical computations, percentages, or numeric evaluations. Never compute arithmetic in your head.
2. Use 'search_tool' to retrieve live facts, demographic statistics, or external information. Always extract precise numbers from the search results.
3. Use 'python_tool' only if code review, explanation, or syntax inspection is specifically requested. Python execution is disabled for security.
4. When you answer, cite the sources or URLs provided in the search observations.
5. Provide a direct, concise, and grounded final answer based strictly on tool observations.
"""


class TraceCallbackHandler(BaseCallbackHandler):
    """Callback handler measuring tool execution durations and event lifecycles."""

    def __init__(self):
        super().__init__()
        self.durations: Dict[str, float] = {}
        self._tool_starts: Dict[str, Dict[str, Any]] = {}

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        tool_call_id = kwargs.get("tool_call_id")
        self._tool_starts[run_id] = {
            "start_time": time.perf_counter(),
            "tool_call_id": tool_call_id,
        }

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        info = self._tool_starts.pop(run_id, {})
        start_t = info.get("start_time", time.perf_counter())
        elapsed = round(time.perf_counter() - start_t, 3)

        tool_call_id = info.get("tool_call_id")
        if tool_call_id:
            self.durations[str(tool_call_id)] = elapsed
        if run_id:
            self.durations[run_id] = elapsed


def generate_decision_summary(tool_name: str, tool_input: Any) -> str:
    """Generate an objective, fact-based summary explaining the tool invocation.

    Avoids fabricating internal model reasoning or private thoughts.
    """
    clean_name = (tool_name or "").lower()

    if "search" in clean_name:
        query = ""
        if isinstance(tool_input, dict):
            query = tool_input.get("query", "")
        elif isinstance(tool_input, str):
            query = tool_input
        if query:
            return f"The agent needs current factual data or web verification, so it searches for: '{query}'."
        return "The agent needs current factual data, so it searches the web."

    elif "calc" in clean_name:
        expr = ""
        if isinstance(tool_input, dict):
            expr = tool_input.get("expression", "")
        elif isinstance(tool_input, str):
            expr = tool_input
        if expr:
            return f"The agent needs an exact arithmetic evaluation, so it computes: {expr}."
        return "The agent needs exact mathematical computation, so it runs the calculator."

    elif "python" in clean_name:
        return "The agent needs code preview or syntax inspection, so it invokes the Python tool."

    return f"The agent executes {tool_name} to fulfill the user's request."


def generate_observation_preview(tool_name: str, raw_output: str, max_chars: int = 250) -> str:
    """Generate a clean, shortened preview of tool output."""
    clean_name = (tool_name or "").lower()
    raw_str = (raw_output or "").strip()

    if "search" in clean_name:
        result_count = len(re.findall(r"\[\d+\]", raw_str))
        first_title_match = re.search(r"\[1\]\s*(.+)", raw_str)
        if result_count > 0:
            first_title = first_title_match.group(1).strip() if first_title_match else ""
            if first_title:
                return f"Found {result_count} result snippet(s) and source URLs (Top source: {first_title})."
            return f"Found {result_count} result snippet(s) and source URLs."

    if len(raw_str) <= max_chars:
        return raw_str
    return raw_str[:max_chars].rstrip() + "..."


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


def run_agent(query: str, agent=None, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> Dict[str, Any]:
    """Execute the agent on a user query and return the answer, trace, and citations.

    Args:
        query: User prompt or question string.
        agent: Optional pre-compiled agent runnable.
        max_iterations: Maximum reasoning cycles before halting execution (default: 8).

    Returns:
        Dict containing:
            - output: Final text response (with secrets redacted)
            - trace: List of tool execution events (tool, decision_summary, input, output, preview, duration_seconds, status)
            - sources: Deduplicated list of source URLs discovered during search
            - total_duration_seconds: Float duration in seconds
            - status: "success" or "error"
    """
    if not isinstance(query, str) or not query.strip():
        return {
            "output": "Error: Query cannot be empty.",
            "trace": [],
            "sources": [],
            "total_duration_seconds": 0.0,
            "status": "error",
        }

    clean_query = query.strip()

    try:
        active_agent = agent or build_agent()
    except Exception as e:
        safe_err = redact_secrets(str(e))
        return {
            "output": f"Configuration Error: {safe_err}",
            "trace": [],
            "sources": [],
            "total_duration_seconds": 0.0,
            "status": "error",
        }

    cb_handler = TraceCallbackHandler()
    start_total_t = time.perf_counter()

    try:
        # Each ReAct loop cycle involves model call + tool call, so allow 2 * max_iterations
        recursion_limit = max_iterations * 2
        response = active_agent.invoke(
            {"messages": [{"role": "user", "content": clean_query}]},
            config={"callbacks": [cb_handler], "recursion_limit": recursion_limit},
        )
    except GraphRecursionError:
        return {
            "output": (
                f"Execution Error: Agent reached the maximum iteration limit ({max_iterations} iterations) "
                "without reaching a final answer. Execution was halted to prevent an infinite loop."
            ),
            "trace": [],
            "sources": [],
            "total_duration_seconds": round(time.perf_counter() - start_total_t, 3),
            "status": "error",
        }
    except Exception as e:
        safe_err = redact_secrets(str(e))
        return {
            "output": f"Execution Error: {safe_err}",
            "trace": [],
            "sources": [],
            "total_duration_seconds": round(time.perf_counter() - start_total_t, 3),
            "status": "error",
        }

    total_duration = round(time.perf_counter() - start_total_t, 3)

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
            raw_output = redact_secrets(_extract_text_content(msg.content))

            # Determine execution status
            is_err = "error" in raw_output.lower() and not raw_output.startswith("Security Notice")
            trace_status = "error" if is_err else "success"

            # Duration from callback
            step_duration = cb_handler.durations.get(str(tc_id))

            decision_summary = generate_decision_summary(tool_name, tool_input)
            preview = generate_observation_preview(tool_name, raw_output)

            trace.append({
                "tool": tool_name,
                "decision_summary": decision_summary,
                "input": tool_input,
                "output": raw_output,
                "preview": preview,
                "duration_seconds": step_duration,
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
        "output": redact_secrets(final_answer or "No response generated."),
        "trace": trace,
        "sources": sources,
        "total_duration_seconds": total_duration,
        "status": "success",
    }


def format_trace_display(result: Dict[str, Any]) -> str:
    """Format the agent execution trace into a clean, labeled display matching blueprint Step 9."""
    sections = []

    trace_steps = result.get("trace", [])
    for i, step in enumerate(trace_steps, 1):
        lines = []
        lines.append(f"Decision summary\n{step.get('decision_summary', '')}\n")
        lines.append(f"Tool call: {step.get('tool')}")

        inp = step.get("input", {})
        if isinstance(inp, dict):
            inp_str = ", ".join(f"{k}: {v}" for k, v in inp.items()) if inp else "{}"
        else:
            inp_str = str(inp)
        lines.append(f"Input: {inp_str}")

        dur = step.get("duration_seconds")
        if dur is not None:
            lines.append(f"Duration: {dur:.3f}s")

        lines.append(f"Status: {step.get('status')}")
        lines.append(f"Observation: {step.get('preview', step.get('output', ''))}")
        sections.append("\n".join(lines))

    # Final Answer section
    final_lines = ["Final answer", result.get("output", "")]
    sources = result.get("sources", [])
    if sources:
        final_lines.append("\nSources:")
        for s in sources:
            final_lines.append(f"- {s}")

    if result.get("total_duration_seconds") is not None:
        final_lines.append(f"\nExecution Duration: {result['total_duration_seconds']:.2f}s")

    sections.append("\n".join(final_lines))
    return "\n\n" + ("\n\n" + "-" * 50 + "\n\n").join(sections) + "\n"


def main():
    """Command-line entrypoint to run the agent with trace display."""
    import sys

    # Set UTF-8 encoding for console output
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 65)
    print("REACTRON AGENT: EXECUTION TRACE VIEWER (STEP 9)")
    print("=" * 65)

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = (
            "Search for the latest population estimate for Bangladesh "
            "and calculate 5% of that number."
        )

    print(f"\nUser Query: {query}\n")
    print("Executing ReAct reasoning & tool-use loop...")

    result = run_agent(query)
    print(format_trace_display(result))
    print("=" * 65)


if __name__ == "__main__":
    main()
