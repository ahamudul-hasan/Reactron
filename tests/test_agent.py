"""Unit tests for the Reactron agent module and trace capture (Step 9)."""

import unittest
from unittest.mock import MagicMock, patch
from agent import (
    _extract_text_content,
    format_trace_display,
    generate_decision_summary,
    generate_observation_preview,
    get_llm,
    run_agent,
    TraceCallbackHandler,
)


class TestAgent(unittest.TestCase):
    """Test cases for agent orchestration and trace extraction."""

    def test_extract_text_content_from_string(self):
        """Test text extraction when content is already a string."""
        self.assertEqual(_extract_text_content("hello world"), "hello world")

    def test_extract_text_content_from_structured_list(self):
        """Test text extraction from LangChain / GenAI list of blocks."""
        content = [
            {"type": "text", "text": "Part 1"},
            {"type": "text", "text": "Part 2"},
        ]
        self.assertEqual(_extract_text_content(content), "Part 1\nPart 2")

    def test_run_agent_empty_query(self):
        """Test that empty queries return immediate error without LLM invocation."""
        result = run_agent("")
        self.assertEqual(result["status"], "error")
        self.assertIn("cannot be empty", result["output"])

    def test_run_agent_whitespace_query(self):
        """Test that whitespace queries return error."""
        result = run_agent("    \n\t")
        self.assertEqual(result["status"], "error")
        self.assertIn("cannot be empty", result["output"])

    def test_run_agent_non_string_query(self):
        """Test that non-string queries return error."""
        result = run_agent(12345)  # type: ignore
        self.assertEqual(result["status"], "error")
        self.assertIn("cannot be empty", result["output"])

    def test_get_llm_missing_api_key(self):
        """Test that get_llm raises ValueError when API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                get_llm()

    def test_generate_decision_summary(self):
        """Test factual, objective decision summary generation without fabricated thoughts."""
        # Search tool
        summary_search = generate_decision_summary("search_tool", {"query": "Bangladesh population"})
        self.assertIn("Bangladesh population", summary_search)
        self.assertIn("searches for", summary_search)

        # Calculator tool
        summary_calc = generate_decision_summary("calculator_tool", {"expression": "12 * 8"})
        self.assertIn("12 * 8", summary_calc)
        self.assertIn("computes", summary_calc)

        # Python tool
        summary_py = generate_decision_summary("python_tool", {"code": "print(1)"})
        self.assertIn("code preview or syntax inspection", summary_py)

    def test_generate_observation_preview(self):
        """Test that observation previews are concise and informative."""
        raw_search = (
            "[1] Demographics of Bangladesh\n"
            "    URL: https://en.wikipedia.org/wiki/Demographics_of_Bangladesh\n"
            "    Snippet: Population is 175M.\n\n"
            "[2] World Bank Data\n"
            "    URL: https://data.worldbank.org/country/BD\n"
            "    Snippet: Population is 175M."
        )
        preview = generate_observation_preview("search_tool", raw_search)
        self.assertIn("Found 2 result snippet(s)", preview)
        self.assertIn("Demographics of Bangladesh", preview)

    def test_format_trace_display(self):
        """Test trace formatting matching blueprint Step 9 specification."""
        sample_result = {
            "output": "Using the selected population estimate, 5% is approximately 8.5 million.",
            "trace": [
                {
                    "tool": "search_tool",
                    "decision_summary": "The agent needs a current value, so it searches the web.",
                    "input": {"query": "population estimate Bangladesh"},
                    "output": "Found two result snippets and source URLs.",
                    "preview": "Found two result snippets and source URLs.",
                    "duration_seconds": 0.450,
                    "status": "success",
                },
                {
                    "tool": "calculator_tool",
                    "decision_summary": "The agent needs an exact arithmetic evaluation.",
                    "input": {"expression": "5 / 100 * 170000000"},
                    "output": "8500000",
                    "preview": "8500000",
                    "duration_seconds": 0.002,
                    "status": "success",
                },
            ],
            "sources": ["https://en.wikipedia.org/wiki/Demographics_of_Bangladesh"],
            "total_duration_seconds": 1.25,
            "status": "success",
        }

        display = format_trace_display(sample_result)

        self.assertIn("Decision summary", display)
        self.assertIn("Tool call: search_tool", display)
        self.assertIn("Tool call: calculator_tool", display)
        self.assertIn("Observation: 8500000", display)
        self.assertIn("Final answer", display)
        self.assertIn("https://en.wikipedia.org/wiki/Demographics_of_Bangladesh", display)
        self.assertIn("Execution Duration: 1.25s", display)

    def test_trace_callback_handler(self):
        """Test duration tracking in TraceCallbackHandler."""
        cb = TraceCallbackHandler()
        run_id = "test-run-123"
        tool_call_id = "call-abc"

        cb.on_tool_start({"name": "calculator_tool"}, "2+2", run_id=run_id, tool_call_id=tool_call_id)
        self.assertIn(run_id, cb._tool_starts)

        cb.on_tool_end("4", run_id=run_id)
        self.assertIn(tool_call_id, cb.durations)
        self.assertGreaterEqual(cb.durations[tool_call_id], 0.0)


if __name__ == "__main__":
    unittest.main()
