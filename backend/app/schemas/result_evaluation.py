'''
@create_time: 2026/4/26 下午8:55
@Author: GeChao
@File: result_evaluation.py
'''
from typing import Literal

from pydantic import BaseModel


class ResultEvaluation(BaseModel):
    enough: bool
    next_action: Literal[
        "final_answer",
        "call_rag",
        "call_mcp",
        "call_weather",
        "call_clarification"
    ]
    reason: str

