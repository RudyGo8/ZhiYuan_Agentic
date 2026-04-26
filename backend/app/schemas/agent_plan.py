'''
@create_time: 2026/4/26 下午8:48
@Author: GeChao
@File: agent_plan.py
'''

from pydantic import BaseModel
from typing import Literal


class PlanStep(BaseModel):
    id: str
    type: Literal[
        "load_context",
        "call_tool",
        "evaluate_result",
        "final_answer"
    ]
    tool: str | None = None
    reason: str = ""


class AgentPlan(BaseModel):
    task_type: str
    steps: list[PlanStep]
