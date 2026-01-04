"""Tavily API search tool for claim verification."""

from typing import Any, Dict, List, Optional

from crewai.tools import BaseTool
from pydantic import Field

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TavilySearchTool(BaseTool):
    """Tool to search the web using Tavily API for claim verification."""

    name: str = "tavily_search"
    description: str = (
        "Search the web using Tavily API to find evidence for or against a claim. "
        "Returns search results with URLs, titles, and content snippets. "
        "Use this for fact-checking and finding supporting or refuting evidence."
    )

    max_results: int = Field(default=10, description="Maximum number of search results")

    def _run(self, query: str) -> Dict[str, Any]:
        """Execute a Tavily search for the given query.

        Args:
            query: The search query (typically a claim to verify)

        Returns:
            Dict containing search results

        Raises:
            RuntimeError: If API key is not configured or search fails
        """
        # Check for API key - FAIL FAST with clear error
        api_key = settings.tavily_api_key
        if not api_key:
            error_msg = (
                "TAVILY_API_KEY is not configured. "
                "Web search cannot proceed without a valid API key. "
                "Please set TAVILY_API_KEY in your .env file. "
                "Get your API key at https://tavily.com"
            )
            logger.error("Tavily API key not configured - ABORTING SEARCH")
            # Raise exception to stop the agent from hallucinating results
            raise RuntimeError(error_msg)

        try:
            from tavily import TavilyClient
        except ImportError:
            error_msg = "tavily-python package not installed. Run: pip install tavily-python"
            logger.error("Tavily package not installed - ABORTING SEARCH")
            raise RuntimeError(error_msg)

        try:
            client = TavilyClient(api_key=api_key)

            # Perform the search
            search_response = client.search(
                query=query,
                max_results=self.max_results,
                include_answer=False,  # We'll generate our own conclusion
                include_raw_content=False,  # Snippets are sufficient for MVP
            )

            # Extract results
            results = []
            for item in search_response.get("results", []):
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "score": item.get("score", 0.0),
                })

            if not results:
                logger.warning(f"Tavily search returned 0 results for: {query[:50]}...")
                raise RuntimeError(
                    f"Web search returned no results for this claim. "
                    f"The claim may be too specific or the search terms need adjustment."
                )

            logger.info(f"Tavily search returned {len(results)} results for: {query[:50]}...")

            return {
                "query": query,
                "results": results,
                "success": True,
                "error": None,
            }

        except RuntimeError:
            # Re-raise our own errors
            raise

        except Exception as e:
            error_msg = f"Tavily search failed: {str(e)}"
            logger.error(f"Tavily search error: {e}")
            raise RuntimeError(error_msg)


def search_for_claim(
    claim_text: str,
    max_results: int = 10
) -> Dict[str, Any]:
    """Convenience function to search for evidence about a claim.

    Args:
        claim_text: The claim to search for
        max_results: Maximum number of results to return

    Returns:
        Dict with search results

    Raises:
        RuntimeError: If search fails or API key is not configured
    """
    tool = TavilySearchTool(max_results=max_results)
    return tool._run(claim_text)


def search_for_evidence(
    claim_text: str,
    search_type: str = "general"
) -> Dict[str, Any]:
    """Search for evidence with different search strategies.

    Args:
        claim_text: The claim to verify
        search_type: Type of search - "general", "supporting", or "refuting"

    Returns:
        Dict with search results

    Raises:
        RuntimeError: If search fails or API key is not configured
    """
    if search_type == "supporting":
        query = f"evidence supporting: {claim_text}"
    elif search_type == "refuting":
        query = f"evidence against: {claim_text}"
    else:
        query = claim_text

    return search_for_claim(query)
