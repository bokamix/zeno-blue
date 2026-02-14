"""
web_search tool - Search the web using Serper API (Google Search).

Provides search results for research tasks, fact-checking,
finding current information, etc.
"""

from typing import Any, Dict, List, Optional

import httpx

from user_container.tools.registry import ToolSchema, make_parameters


WEB_SEARCH_SCHEMA = ToolSchema(
    name="web_search",
    description="""Search the web using Google (via Serper API).

USE FOR:
- Research tasks requiring current/up-to-date information
- Finding facts, news, documentation
- Discovering URLs to fetch with web_fetch
- Answering questions about recent events

Returns: List of search results with title, link, snippet.

WORKFLOW: Use web_search to find relevant URLs, then web_fetch to read full content.""",
    parameters=make_parameters(
        properties={
            "query": {
                "type": "string",
                "description": "Search query (like you'd type into Google)"
            },
            "num_results": {
                "type": ["integer", "null"],
                "description": "Number of results to return (default: 10, max: 100)"
            },
            "search_type": {
                "type": ["string", "null"],
                "description": "Type of search: 'search' (default), 'news', 'images'"
            }
        },
        required=["query"]
    )
)


def make_web_search_tool(api_key: Optional[str]):
    """Create the web_search tool handler with API key."""

    def web_search(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search the web using Serper API.

        Args (via dict):
            query: Search query
            num_results: Number of results (default 10)
            search_type: 'search', 'news', or 'images'

        Returns:
            Dict with query, results list, and metadata
        """
        if not api_key:
            return {
                "status": "error",
                "error": "SERPER_API_KEY not configured. Set it in environment variables."
            }

        query = args.get("query", "").strip()
        if not query:
            return {"status": "error", "error": "Query is required"}

        num_results = min(args.get("num_results") or 10, 100)
        search_type = args.get("search_type") or "search"

        # Map search type to Serper endpoint
        endpoint_map = {
            "search": "https://google.serper.dev/search",
            "news": "https://google.serper.dev/news",
            "images": "https://google.serper.dev/images",
        }

        endpoint = endpoint_map.get(search_type, endpoint_map["search"])

        try:
            response = httpx.post(
                endpoint,
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": num_results
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Parse results based on search type
            results = _parse_serper_response(data, search_type)

            return {
                "status": "success",
                "query": query,
                "search_type": search_type,
                "results": results,
                "num_results": len(results)
            }

        except httpx.TimeoutException:
            return {"status": "error", "query": query, "error": "Search request timed out"}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "query": query, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"status": "error", "query": query, "error": str(e)}

    return web_search


def _parse_serper_response(data: Dict[str, Any], search_type: str) -> List[Dict[str, Any]]:
    """Parse Serper API response into clean results."""
    results = []

    if search_type == "search":
        # Organic search results
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position")
            })

        # Add knowledge graph if present (useful for quick facts)
        kg = data.get("knowledgeGraph")
        if kg:
            results.insert(0, {
                "type": "knowledge_graph",
                "title": kg.get("title", ""),
                "description": kg.get("description", ""),
                "attributes": kg.get("attributes", {})
            })

        # Add answer box if present
        answer = data.get("answerBox")
        if answer:
            results.insert(0, {
                "type": "answer_box",
                "title": answer.get("title", ""),
                "answer": answer.get("answer") or answer.get("snippet", ""),
                "link": answer.get("link", "")
            })

    elif search_type == "news":
        for item in data.get("news", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "date": item.get("date", "")
            })

    elif search_type == "images":
        for item in data.get("images", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "image_url": item.get("imageUrl", ""),
                "source": item.get("source", "")
            })

    return results
