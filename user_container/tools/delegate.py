"""
delegate_task tool - Delegate atomic tasks to a fast worker agent.

This tool allows the main agent to offload self-contained tasks to a
lightweight DelegateExecutor running on Haiku. Multiple delegate_task
calls can run in parallel via asyncio.gather.
"""

from typing import Dict, Any

from user_container.agent.delegate_executor import DelegateExecutor
from user_container.tools.registry import ToolSchema, make_parameters


DELEGATE_TASK_SCHEMA = ToolSchema(
    name="delegate_task",
    description="""Delegate a task to a fast worker agent that runs IN PARALLEL with other delegates.

USE WHEN (any of these):
- You need to research/fetch/analyze MULTIPLE things (each becomes a delegate)
- Task has 3+ steps to complete
- Result is a "finished product" (summary, report, data extraction)

PARALLEL RESEARCH PATTERN:
When user asks to research/compare/find multiple things, spawn multiple delegate_task calls:
- "Compare companies A, B, C" → 3x delegate_task (one per company)
- "Find trends in X, Y, Z" → 3x delegate_task (one per topic)
- "Search for info about topic" → 3-4x delegate_task (different search angles)

Each delegate can use web_search, web_fetch internally. They run in parallel = faster!

DO NOT USE:
- Single file read/write (do it yourself)
- When you need result of task A before starting task B
- When task needs user interaction

GOOD: 3x delegate_task("Research [topic1/2/3] and summarize findings")
GOOD: delegate_task("Fetch https://url and extract key points")
BAD:  delegate_task("Read config.json")  // single operation, do yourself""",
    parameters=make_parameters(
        properties={
            "task": {
                "type": "string",
                "description": "Clear, self-contained task description"
            },
            "context": {
                "type": ["string", "null"],
                "description": "Optional: URLs, file paths, or data needed for the task"
            }
        },
        required=["task"]
    )
)


def make_delegate_task_tool(executor: DelegateExecutor):
    """
    Create a delegate_task handler bound to the given executor.

    Args:
        executor: DelegateExecutor instance to use

    Returns:
        Handler function for the delegate_task tool
    """
    def delegate_task(args: Dict[str, Any]) -> Dict[str, Any]:
        task = args.get("task", "")
        context = args.get("context", "") or ""

        result = executor.execute(task, context)

        return {
            "status": result.status,
            "output": result.output,
            "steps": result.steps,
            "error": result.error
        }

    return delegate_task
