import os
from typing import Optional
from dotenv import load_dotenv
from langchain_core.tools import tool
from tavily import (
    BadRequestError,
    InvalidAPIKeyError,
    TavilyClient,
    UsageLimitExceededError,
)

load_dotenv()

MAX_QUERY_LENGTH = 300
DEFAULT_MAX_RESULTS = 3


def _clean_text(text: str) -> str:
    """Normalize text and replace problematic unicode punctuation."""
    if not text:
        return ""
    return (
        text.replace("\u2212", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .strip()
    )


def tavily_search(query: str, max_results: int = DEFAULT_MAX_RESULTS, api_key: Optional[str] = None) -> str:
    if not isinstance(query, str):
        return "Error: Search query must be a string."

    clean_query = query.strip()
    if not clean_query:
        return "Error: Search query cannot be empty."

    if len(clean_query) > MAX_QUERY_LENGTH:
        return f"Error: Search query exceeds maximum length of {MAX_QUERY_LENGTH} characters."

    # Resolve API key
    key = api_key or os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        return (
            "Error: TAVILY_API_KEY is missing or not configured. "
            "Please set your Tavily API key in the .env file or environment variables."
        )

    try:
        client = TavilyClient(api_key=key)
        response = client.search(
            query=clean_query,
            max_results=max_results,
            search_depth="basic",
        )

        results = response.get("results", [])
        if not results:
            return f"No search results found for: '{clean_query}'."

        formatted_outputs = []
        for i, item in enumerate(results, 1):
            title = _clean_text(item.get("title", "Untitled"))
            url = item.get("url", "").strip()
            content = _clean_text(item.get("content", ""))

            formatted_outputs.append(
                f"[{i}] {title}\n"
                f"    URL: {url}\n"
                f"    Snippet: {content}"
            )

        return "\n\n".join(formatted_outputs)

    except InvalidAPIKeyError:
        return "Error: Invalid Tavily API key. Please check your credentials."
    except UsageLimitExceededError:
        return "Error: Tavily API usage limit or rate limit exceeded. Please try again later."
    except BadRequestError as e:
        return f"Error: Tavily search bad request: {e}"
    except Exception as e:
        return f"Error connecting to Tavily search service: {e}"


@tool
def search_tool(query: str) -> str:
    """Search the web for current facts, statistics, population data, or news.

    Use this tool whenever you need up-to-date information or data that requires
    verification from external web sources.

    Args:
        query: The search query string (e.g., 'latest population estimate for Bangladesh').
    """
    return tavily_search(query)

