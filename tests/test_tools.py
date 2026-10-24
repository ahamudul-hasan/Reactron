"""Unit tests for the Tavily search tool."""

import os
import unittest
from unittest.mock import MagicMock, patch
from tavily import InvalidAPIKeyError, UsageLimitExceededError
from tools.search_tool import search_tool, tavily_search


class TestSearchTool(unittest.TestCase):
    """Test cases for the Tavily search tool."""

    def test_search_missing_api_key(self):
        """Test that missing or empty API key produces a helpful error."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=False):
            result = tavily_search("test query", api_key="")
            self.assertIn("Error: TAVILY_API_KEY is missing or not configured", result)

    def test_search_empty_query(self):
        """Test rejection of empty or whitespace query."""
        self.assertIn("Error: Search query cannot be empty", tavily_search(""))
        self.assertIn("Error: Search query cannot be empty", tavily_search("   "))

    def test_search_non_string_query(self):
        """Test rejection of non-string query."""
        self.assertIn("Error: Search query must be a string", tavily_search(123))

    def test_search_normal_query_mocked(self):
        """Test that a normal query returns formatted titles, snippets, and URLs."""
        fake_response = {
            "results": [
                {
                    "title": "Bangladesh Population (2026)",
                    "url": "https://www.worldometers.info/world-population/bangladesh-population",
                    "content": "The current population of Bangladesh is approximately 177 million.",
                },
                {
                    "title": "Demographics of Bangladesh",
                    "url": "https://en.wikipedia.org/wiki/Demographics_of_Bangladesh",
                    "content": "Bangladesh is the eighth-most populous country in the world.",
                },
            ]
        }

        with patch("tools.search_tool.TavilyClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.search.return_value = fake_response
            mock_client_cls.return_value = mock_client

            result = tavily_search("population Bangladesh", api_key="fake-key")

            self.assertIn("Bangladesh Population (2026)", result)
            self.assertIn("https://www.worldometers.info", result)
            self.assertIn("Snippet:", result)
            self.assertIn("URL:", result)

    def test_search_invalid_key_error(self):
        """Test handling of InvalidAPIKeyError."""
        with patch("tools.search_tool.TavilyClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.search.side_effect = InvalidAPIKeyError("Invalid API key")
            mock_client_cls.return_value = mock_client

            result = tavily_search("test", api_key="bad-key")
            self.assertIn("Error: Invalid Tavily API key", result)

    def test_search_rate_limit_error(self):
        """Test handling of UsageLimitExceededError."""
        with patch("tools.search_tool.TavilyClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.search.side_effect = UsageLimitExceededError("Rate limit reached")
            mock_client_cls.return_value = mock_client

            result = tavily_search("test", api_key="any-key")
            self.assertIn("usage limit or rate limit exceeded", result)

    def test_search_network_error(self):
        """Test handling of generic network/connection failure."""
        with patch("tools.search_tool.TavilyClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.search.side_effect = ConnectionError("DNS resolution failed")
            mock_client_cls.return_value = mock_client

            result = tavily_search("test", api_key="any-key")
            self.assertIn("Error connecting to Tavily search service", result)

    def test_langchain_search_tool_invocation(self):
        """Test calling the LangChain wrapped tool."""
        fake_response = {
            "results": [
                {
                    "title": "Example Title",
                    "url": "https://example.com",
                    "content": "Example content",
                }
            ]
        }

        with patch("tools.search_tool.TavilyClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.search.return_value = fake_response
            mock_client_cls.return_value = mock_client

            result = search_tool.invoke({"query": "example query"})
            self.assertIn("Example Title", result)
            self.assertIn("https://example.com", result)

    def test_search_live_api(self):
        """Test live API call if TAVILY_API_KEY is configured in .env."""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            self.skipTest("TAVILY_API_KEY not configured, skipping live API test.")

        result = tavily_search("latest population Bangladesh", max_results=1)
        self.assertNotIn("Error:", result)
        self.assertIn("http", result)
        self.assertIn("Snippet:", result)


if __name__ == "__main__":
    unittest.main()
