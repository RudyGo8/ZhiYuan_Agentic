'''
@create_time: 2026/4/26 下午9:13
@Author: GeChao
@File: intent_service.py
'''

import re
from app.schemas.agent_intent import AgentIntent


class IntentService:
    RAG_KEYWORDS = (
        "知识库", "文档", "资料", "上传", "根据文档", "根据资料",
        "内部知识", "项目知识", "检索", "引用", "出处",
        "knowledge base", "document", "uploaded",
    )

    REALTIME_KEYWORDS = (
        "最新", "当前", "最近", "今天", "实时", "现在",
        "latest", "current", "recent", "today", "now",
    )

    WEATHER_KEYWORDS = (
        "天气", "气温", "温度", "下雨", "weather", "temperature", "rain",
    )

    DATABASE_KEYWORDS = (
        "数据库", "数据表", "表结构", "sql", "mysql", "schema",
    )

    CASUAL_KEYWORDS = (
        "你好", "您好", "hello", "hi", "谢谢", "thanks",
    )

    MCP_INTEGRATION_KEYWORDS = (
        "接入mcp",
        "添加mcp",
        "配置mcp",
        "mcp server",
        "mcp服务",
        "model context protocol",
        "stdio",
        "sse",
        "websocket",
        "http mcp",
        ".mcp.json",
    )

    @staticmethod
    def _normalize(text: str) -> str:
        return (text or "").strip().lower()

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    def classify(self, user_text: str) -> AgentIntent:
        text = self._normalize(user_text)

        if not text:
            return AgentIntent(
                intent="unknown",
                need_tools=False,
                tool_candidates=[],
                confidence=0.3,
                reason="用户输入为空",
            )

        if self._contains_any(text, self.WEATHER_KEYWORDS):
            return AgentIntent(
                intent="weather_query",
                need_tools=True,
                tool_candidates=["weather"],
                required_realtime=True,
                confidence=0.9,
                reason="命中天气相关关键词",
            )

        if self._contains_any(text, self.RAG_KEYWORDS):
            return AgentIntent(
                intent="rag_qa",
                need_tools=True,
                tool_candidates=["rag"],
                required_knowledge_base=True,
                confidence=0.85,
                reason="需要基于知识库或文档回答",
            )

        if self._contains_any(text, self.MCP_INTEGRATION_KEYWORDS):
            return AgentIntent(
                intent="mcp_integration",
                need_tools=True,
                tool_candidates=["project_file_reader", "project_code_editor", "project_shell"],
                confidence=0.9,
                reason="用户要求接入或配置 MCP Server",
            )

        if self._contains_any(text, self.REALTIME_KEYWORDS):
            return AgentIntent(
                intent="realtime_query",
                need_tools=True,
                tool_candidates=["mcp"],
                required_realtime=True,
                confidence=0.75,
                reason="需要实时信息",
            )

        if self._contains_any(text, self.DATABASE_KEYWORDS):
            return AgentIntent(
                intent="database_query",
                need_tools=True,
                tool_candidates=["database"],
                confidence=0.75,
                reason="命中数据库相关关键词",
            )

        if self._contains_any(text, self.CASUAL_KEYWORDS) and len(text) <= 30:
            return AgentIntent(
                intent="casual_chat",
                need_tools=False,
                tool_candidates=[],
                confidence=0.8,
                reason="普通问候或闲聊",
            )

        return AgentIntent(
            intent="unknown",
            need_tools=False,
            tool_candidates=[],
            confidence=0.5,
            reason="未识别明确工具需求",
        )



intent_service = IntentService()
