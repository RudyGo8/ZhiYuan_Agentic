'''
@create_time: 2026/4/28 上午12:16
@Author: GeChao
@File: rag_tools.py
'''

from langchain_core.tools import tool

from app.rag.formatter import format_docs
from app.tools.runtime import (
    get_knowledge_tool_call_this_turn,
    increase_knowledge_tool_calls_this_turn,
    set_last_rag_context)


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """工具：检索知识库"""
    calls_this_turn = get_knowledge_tool_call_this_turn()
    if calls_this_turn >= 1:
        return (
            "TOOL_CALL_LIMIT_REACHED: search_knowledge_base has already been called once in this turn. "
            "Use the existing retrieval result and provide the final answer directly."
        )

    increase_knowledge_tool_calls_this_turn()

    from app.rag import run_rag_graph

    rag_result = run_rag_graph(query)

    docs = rag_result.get("docs", []) if isinstance(rag_result, dict) else []
    rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
    if rag_trace:
        set_last_rag_context({"rag_trace": rag_trace})

    if not docs:
        return "No relevant documents found in the knowledge base."

    formatted = format_docs(docs)
    return "Retrieved Chunks:\n" + "\n\n---\n\n".join(formatted)
