from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

_MCP_CALLS: ContextVar[list[dict[str, Any]]] = ContextVar("_MCP_CALLS", default=[])


def reset_mcp_trace() -> None:
    _MCP_CALLS.set([])


def append_mcp_trace(call: dict[str, Any]) -> None:
    items = list(_MCP_CALLS.get())
    items.append(call)
    _MCP_CALLS.set(items)


def get_mcp_trace(clear: bool = True) -> list[dict[str, Any]]:
    items = list(_MCP_CALLS.get())
    if clear:
        _MCP_CALLS.set([])
    return items


def new_mcp_call(
    *,
    server_name: str,
    tool_name: str,
    query: str,
    success: bool,
    duration_ms: int,
    result_summary: str,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "source_type": "mcp",
        "server_name": server_name,
        "tool_name": tool_name,
        "query": query,
        "success": success,
        "duration_ms": duration_ms,
        "result_summary": result_summary,
        "error": error,
    }

