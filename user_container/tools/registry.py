"""
Tool Registry with schema support for OpenAI function calling.

This module provides a clean, extensible way to register tools with their
OpenAI-compatible schemas. Tools can be registered via decorator or direct call.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import functools
import inspect
import time


@dataclass
class ToolSchema:
    """OpenAI function-calling compatible tool schema."""

    name: str
    description: str
    parameters: Dict[str, Any]
    strict: bool = False

    def to_openai_spec(self) -> Dict[str, Any]:
        """Convert to OpenAI Responses API tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": self.strict,
                "parameters": self.parameters,
            }
        }


@dataclass
class RegisteredTool:
    """A registered tool with its handler and schema."""

    name: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    schema: ToolSchema
    defaults: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Registry for agent tools.

    Supports registration via decorator or direct call.
    Each tool has a handler function and an OpenAI-compatible schema.
    """

    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
        schema: ToolSchema,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a tool with its handler and schema."""
        self._tools[name] = RegisteredTool(
            name=name,
            handler=handler,
            schema=schema,
            defaults=defaults or {},
        )

    def get(self, name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        """Return tool names with descriptions."""
        return {name: tool.schema.description for name, tool in self._tools.items()}

    def get_openai_specs(self) -> List[Dict[str, Any]]:
        """Get all tool schemas in OpenAI format."""
        return [tool.schema.to_openai_spec() for tool in self._tools.values()]

    def call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool by name with arguments.

        Applies default values for missing optional parameters.
        Logs tool execution to Langfuse for observability.
        """
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Unknown tool: {name}")

        # Apply defaults for missing/null values
        merged_args = dict(tool.defaults)
        for key, value in args.items():
            if value is not None:
                merged_args[key] = value

        # Execute tool and measure duration
        start_time = time.time()
        is_error = False
        result = None
        try:
            result = tool.handler(merged_args)
        except Exception as e:
            is_error = True
            result = {"error": str(e)}
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            # Log to Langfuse (observability)
            try:
                from user_container.observability import log_tool_span
                log_tool_span(
                    tool_name=name,
                    args=merged_args,
                    result=result,
                    is_error=is_error,
                    duration_ms=duration_ms,
                )
            except ImportError:
                pass  # Observability module not available

        return result


def make_parameters(
    properties: Dict[str, Dict[str, Any]],
    required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Helper to create OpenAI-compatible parameters schema.

    For strict mode, all properties must be listed as required,
    but optional ones should have nullable types.
    """
    # In strict mode, all fields must be required
    all_keys = list(properties.keys())
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required if required is not None else all_keys,
    }
