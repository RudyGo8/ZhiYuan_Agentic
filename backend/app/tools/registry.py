from dataclasses import dataclass
from typing import Callable
from app.tools.rag_tools import search_knowledge_base
from app.tools.weather_tools import get_current_weather


@dataclass
class ToolSpec:
    name: str
    tool: Callable
    description: str
    tags: list[str]
    source: str | None = None


TOOL_REGISTRY = {
    "get_current_weather": ToolSpec(
        name="get_current_weather",
        tool=get_current_weather,
        description="查询当前天气、气温、降雨、温度等实时天气信息",
        tags=["天气", "气温", "温度", "下雨", "weather"],
    ),
    "search_knowledge_base": ToolSpec(
        name="search_knowledge_base",
        tool=search_knowledge_base,
        description="查询用户上传文档、知识库、项目资料、内部知识，并返回有依据的检索结果",
        tags=["知识库", "文档", "资料", "上传", "引用", "rag"],
    ),
}
