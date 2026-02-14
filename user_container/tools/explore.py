"""
explore tool - Explore codebase and get a SUMMARY of findings.

This tool allows the main agent to explore files/code without polluting
its context with raw file contents. The ExploreExecutor runs on Haiku
with read-only tools and returns a concise summary.

Key benefit: Instead of 50 read_file results in main agent context,
you get one summary message with the key findings.
"""

from typing import Dict, Any

from user_container.agent.explore_executor import ExploreExecutor
from user_container.tools.registry import ToolSchema, make_parameters


EXPLORE_SCHEMA = ToolSchema(
    name="explore",
    description="""Explore codebase/files and get a SUMMARY of findings.

USE FOR:
- Understanding project structure before making changes
- Finding where something is implemented
- Searching for patterns across files
- Reading multiple files to understand context
- Any exploration that might need 3+ read/search operations

RETURNS: Concise summary of findings (NOT raw file contents)

BENEFITS:
- Doesn't pollute your context with raw file contents
- Faster (uses cheap model for exploration)
- More thorough (can read many files without context bloat)

Examples:
  explore("Find how authentication works in this project")
  → "Auth in auth.py:45-80. Uses JWT tokens stored in Redis.
     Login endpoint: api/routes.py:120. Middleware: middleware/auth.py"

  explore("What's the database schema?")
  → "SQLite with tables: users, sessions, items.
     Schema in db/models.py. Migrations in db/migrations/"

  explore("Find all API endpoints", paths=["/workspace/api"])
  → "Endpoints in api/routes.py: GET /users (line 20), POST /auth (line 45)..."

DO NOT USE WHEN:
- You need a specific file's exact content (use read_file directly)
- Single quick search (use search_in_files directly)
- You already know exactly where to look""",
    parameters=make_parameters(
        properties={
            "question": {
                "type": "string",
                "description": "What you want to find/understand about the codebase"
            },
            "paths": {
                "type": ["array", "null"],
                "items": {"type": "string"},
                "description": "Optional: specific paths to focus on (e.g., ['/workspace/src', '/workspace/lib'])"
            }
        },
        required=["question"]
    )
)


def make_explore_tool(executor: ExploreExecutor):
    """
    Create an explore handler bound to the given executor.

    Args:
        executor: ExploreExecutor instance to use

    Returns:
        Handler function for the explore tool
    """
    def explore(args: Dict[str, Any]) -> Dict[str, Any]:
        question = args.get("question", "")
        paths = args.get("paths") or None

        result = executor.execute(question, paths)

        return {
            "status": result.status,
            "summary": result.summary,
            "steps": result.steps,
            "error": result.error
        }

    return explore
