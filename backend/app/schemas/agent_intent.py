'''
@create_time: 2026/4/26 下午8:41
@Author: GeChao
@File: agent_intent.py
'''
from typing import Literal

from pydantic import BaseModel


class AgentIntent(BaseModel):
    intent: Literal[
        "casual_chat",
        "rag_qa",
        "realtime_query",
        "weather_query",
        "document_management",
        "database_query",
        "mcp_integration",
        "unknown"
    ]
    need_tools: bool
    tool_candidates: list[str]
    required_realtime: bool = False
    required_knowledge_base: bool = False
    confidence: float
    reason: str
