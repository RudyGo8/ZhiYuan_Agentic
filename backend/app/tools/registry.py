'''
@create_time: 2026/4/28 上午12:24
@Author: GeChao
@File: registry.py
'''

from app.tools.rag_tools import search_knowledge_base
from app.tools.weather_tools import get_current_weather
# from app.tools.project_tools import (
#     ProjectFileReaderTool,
#     ProjectCodeEditorTool,
#     ProjectShellTool,
# )

TOOL_REGISTRY = {
    "search_knowledge_base": search_knowledge_base,
    "get_current_weather": get_current_weather,

    # "project_file_reader": ProjectFileReaderTool(),
    # "project_code_editor": ProjectCodeEditorTool(),
    # "project_shell": ProjectShellTool(),
}


def get_tool(name: str):
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        raise ValueError(
            f"工具未注册：{name}, 当前可用工具: {list(TOOL_REGISTRY.keys())}"
        )
    return TOOL_REGISTRY.get(name)


def list_tools():
    return list(TOOL_REGISTRY.keys())
