"""Reactron Streamlit Web Application (Step 10).

An interactive, production-grade observability UI for the Reactron ReAct Agent,
featuring real-time reasoning loops, deterministic math, grounded web search,
and inspectable tool execution traces.
"""

import html
import os
import time
from typing import Any, Dict, List
import streamlit as st
from dotenv import load_dotenv

from agent import DEFAULT_MODEL, run_agent

load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Reactron ⚡ ReAct Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styling ---
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 0.4rem;
    }
    .badge-success {
        background-color: #064E3B;
        color: #6EE7B7;
        border: 1px solid #059669;
    }
    .badge-tool {
        background-color: #1E293B;
        color: #38BDF8;
        border: 1px solid #0284C7;
    }
    .badge-duration {
        background-color: #312E81;
        color: #C7D2FE;
        border: 1px solid #4338CA;
    }
    .trace-card {
        background-color: rgba(30, 41, 59, 0.4);
        border: 1px solid #334155;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }
    .decision-box {
        background-color: rgba(56, 189, 248, 0.08);
        border-left: 3px solid #38BDF8;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.6rem;
        border-radius: 0 0.375rem 0.375rem 0;
        font-size: 0.95rem;
    }
    .source-chip {
        display: inline-block;
        background-color: #1E293B;
        border: 1px solid #475569;
        border-radius: 0.375rem;
        padding: 0.25rem 0.5rem;
        font-size: 0.8rem;
        margin: 0.2rem 0.3rem 0.2rem 0;
        text-decoration: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_tool_icon(tool_name: str) -> str:
    """Return appropriate icon for each tool."""
    name = (tool_name or "").lower()
    if "search" in name:
        return "🌐"
    if "calc" in name:
        return "🧮"
    if "python" in name:
        return "🔒"
    return "⚙️"


# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚡ Reactron Control Panel")
    st.markdown(
        "A production-grade ReAct agent architecture with grounded web retrieval "
        "and deterministic arithmetic computation."
    )

    st.markdown("---")
    st.markdown("#### 🛠️ System Toolbelt")

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Orchestrator")
        st.markdown(f"**`{DEFAULT_MODEL}`**")
        st.caption("Math Engine")
        st.markdown("**`NumExpr (C-AST)`**")
    with col2:
        st.caption("Search Provider")
        st.markdown("**`Tavily API`**")
        st.caption("Code Sandbox")
        st.markdown("**`Disabled (Safe)`**")

    st.markdown("---")
    st.markdown("#### 💡 Example Queries")

    examples = [
        "Search for the latest population estimate for Bangladesh and calculate 5% of that number.",
        "What is 12 multiplied by 8?",
        "Calculate (150 - 120) / 120 * 100",
        "Who is the current president of France?",
        "Show a preview of a Python function that reverses a string.",
    ]

    for ex in examples:
        if st.button(ex, key=f"ex_{hash(ex)}", use_container_width=True):
            st.session_state.pending_query = ex
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_query = None
        st.rerun()

    st.caption("Reactron v1.0 • Built with LangChain & Streamlit")


# --- Main Header ---
st.markdown(
    '<div class="main-header">⚡ Reactron Agent Studio</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">Inspectable, multi-step problem solving with real-time web search and deterministic arithmetic.</div>',
    unsafe_allow_html=True,
)


# --- Helper: Render a Chat Interaction ---
def render_interaction(item: Dict[str, Any], is_latest: bool = False):
    query = item.get("query", "")
    result = item.get("result", {})
    output = result.get("output", "")
    trace = result.get("trace", [])
    sources = result.get("sources", [])
    total_dur = result.get("total_duration_seconds", 0.0)
    status = result.get("status", "success")

    # User message
    with st.chat_message("user", avatar="👤"):
        st.write(query)

    # Assistant message
    with st.chat_message("assistant", avatar="⚡"):
        if status == "error":
            st.error(output)
            return

        # 1. Final Answer
        st.markdown("#### Final Answer")
        st.markdown(output)

        # 2. Source Citations
        if sources:
            st.markdown("##### 📚 Verified Sources")
            cols = st.columns(min(len(sources), 3))
            for i, src in enumerate(sources):
                st.markdown(f"- [{src}]({src})")

        # 3. Badges Metadata
        st.markdown(
            f'<div style="margin: 0.8rem 0 0.4rem 0;">'
            f'<span class="badge badge-duration">⏱️ {total_dur:.2f}s total</span>'
            f'<span class="badge badge-tool">🛠️ {len(trace)} tool call(s)</span>'
            f'<span class="badge badge-success">✓ Grounded</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # 4. Expandable Execution Trace
        if trace:
            expander_title = f"🔍 View Execution Trace ({len(trace)} step{'s' if len(trace) > 1 else ''})"
            with st.expander(expander_title, expanded=is_latest):
                for idx, step in enumerate(trace, 1):
                    tool_name = step.get("tool", "tool")
                    icon = get_tool_icon(tool_name)
                    dur = step.get("duration_seconds")
                    dur_str = f" • ⏱️ {dur:.3f}s" if dur is not None else ""
                    step_status = step.get("status", "success")
                    badge_class = "badge-success" if step_status == "success" else "badge-error"

                    st.markdown(
                        f"""
                        <div class="trace-card">
                            <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.4rem;">
                                {icon} Step {idx}: <code>{html.escape(tool_name)}</code>
                                <span class="badge {badge_class}">{step_status}</span>
                                <span style="font-size: 0.8rem; color: #94A3B8;">{dur_str}</span>
                            </div>
                            <div class="decision-box">
                                <strong>Decision summary:</strong> {html.escape(step.get('decision_summary', ''))}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.caption("Tool Input")
                        st.json(step.get("input", {}))
                    with c2:
                        st.caption("Observation")
                        raw_out = step.get("output", "")
                        if len(raw_out) > 500:
                            st.text_area(
                                "Observation Details",
                                value=raw_out,
                                height=150,
                                key=f"obs_{idx}_{hash(raw_out)}",
                                disabled=True,
                            )
                        else:
                            st.code(raw_out, language="text")


# --- Render Conversation History ---
for i, item in enumerate(st.session_state.messages):
    is_latest = i == len(st.session_state.messages) - 1
    render_interaction(item, is_latest=is_latest)


# --- Process Query Function ---
def handle_query(query_text: str):
    clean_text = query_text.strip()
    if not clean_text:
        st.warning("Please enter a question or calculation.")
        return

    # Add user message to history placeholder
    with st.chat_message("user", avatar="👤"):
        st.write(clean_text)

    # Agent execution with progress spinner
    with st.chat_message("assistant", avatar="⚡"):
        with st.spinner("Reactron is reasoning and executing tools..."):
            try:
                start_time = time.perf_counter()
                result = run_agent(clean_text)
                elapsed = time.perf_counter() - start_time
                if "total_duration_seconds" not in result or result["total_duration_seconds"] == 0:
                    result["total_duration_seconds"] = round(elapsed, 2)
            except Exception as e:
                result = {
                    "output": f"An unexpected error occurred: {e}",
                    "trace": [],
                    "sources": [],
                    "total_duration_seconds": 0.0,
                    "status": "error",
                }

        # Store in session state
        st.session_state.messages.append({"query": clean_text, "result": result})
        st.rerun()


# --- Input Handling ---
prompt = st.chat_input("Ask Reactron a question (e.g. population, calculation, fact-check)...")

# Check if an example prompt was clicked from sidebar
if st.session_state.pending_query:
    active_prompt = st.session_state.pending_query
    st.session_state.pending_query = None
    handle_query(active_prompt)
elif prompt:
    handle_query(prompt)

