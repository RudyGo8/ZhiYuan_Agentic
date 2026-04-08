from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.mcp.policy import allow_tool


@dataclass
class MCPToolEntry:
    source: str
    name: str
    description: str
    tool: Any


# 工具包装分组注册
def build_registry(raw_tools: list[Any]) -> dict[str, list[MCPToolEntry]]:
    result: dict[str, list[MCPToolEntry]] = defaultdict(list)
    for tool in raw_tools:
        name = getattr(tool, "name", "")
        description = getattr(tool, "description", "") or ""
        if not name:
            continue
        allowed, source = allow_tool(name, description)
        if not allowed or not source:
            continue
        result[source].append(
            MCPToolEntry(
                source=source,
                name=name,
                description=description,
                tool=tool,
            )
        )
    return dict(result)
