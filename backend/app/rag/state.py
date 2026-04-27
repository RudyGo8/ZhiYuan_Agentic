'''
@create_time: 2026/4/27 下午3:58
@Author: GeChao
@File: state.py
'''
from typing import TypedDict, List, Optional


# 检索流程状态定义
class RAGState(TypedDict):
    question: str
    query: str
    context: str
    docs: List[dict]
    route: Optional[str]
    expansion_type: Optional[str]
    expanded_query: Optional[str]
    step_back_question: Optional[str]
    step_back_answer: Optional[str]
    hypothetical_doc: Optional[str]
    rag_trace: Optional[dict]
