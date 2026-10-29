"""Unit tests for the Reactron agent module."""

import unittest
from unittest.mock import MagicMock, patch
from agent import _extract_text_content, run_agent, get_llm


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


if __name__ == "__main__":
    unittest.main()

