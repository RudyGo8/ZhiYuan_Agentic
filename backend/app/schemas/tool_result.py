'''
@create_time: 2026/4/26 下午8:52
@Author: GeChao
@File: tool_result.py
'''

from pydantic import BaseModel


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    content: str
    evidence: list[dict] = []
    trace: dict = {}
    error: str | None = None
