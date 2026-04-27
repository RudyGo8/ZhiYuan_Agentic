'''
@create_time: 2026/4/27 下午1:16
@Author: GeChao
@File: runtime_policy.py
'''
from dataclasses import dataclass, field


@dataclass
class RuntimePolicy:
    name: str = "plan_runtime"
    display_name: str = "Plan-driven Agentic RAG"
    use_mcp: bool = False
    mcp_sources: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    require_rag: bool = False

    def to_trace(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "use_mcp": self.use_mcp,
            "mcp_sources": self.mcp_sources,
            "allowed_tools": self.allowed_tools,
            "require_rag": self.require_rag,
        }


def build_runtime_policy(execution_plan) -> RuntimePolicy:
    allowed_tools = []

    for step in execution_plan.steps:
        if getattr(step, "type", "") == "call_tool" and getattr(step, "tool", None):
            allowed_tools.append(step.tool)

    allowed_tools = list(dict.fromkeys(allowed_tools))
    task_type = getattr(execution_plan, "task_type", "")

    return RuntimePolicy(
        # True
        require_rag=task_type == "rag_qa",
        use_mcp=task_type == "realtime_query",
        mcp_sources=["git"] if task_type == "realtime_query" else [],
        allowed_tools=allowed_tools,
    )
