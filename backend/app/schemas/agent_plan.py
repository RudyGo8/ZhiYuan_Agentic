'''
@create_time: 2026/4/26 下午8:48
@Author: GeChao
@File: agent_plan.py
'''
from pydantic import BaseModel, Field
from typing import Literal, Any


class PlanStep(BaseModel):
    id: str
    type: Literal[
        "load_context",
        "skill_load",
        "tool_call",
        "call_tool",
        "evaluate_result",
        "final_answer"
    ]
    tool: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class AgentPlan(BaseModel):
    task_type: str
    steps: list[PlanStep]
