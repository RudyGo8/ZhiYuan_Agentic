'''
@create_time: 2026/4/27 下午3:58
@Author: GeChao
@File: schema.py
'''

from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional


class GradeDocuments(BaseModel):
    """相关性评估输出结构"""
    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )


class RewriteStrategy(BaseModel):
    """查询重写策略输出结构"""
    strategy: Literal["step_back", "hyde", "complex"]


class RetrieveResult(BaseModel):
    """检索结果结构，后面拆 services 时用"""

    docs: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}


class ExpansionResult(BaseModel):
    """查询扩展结果，后面拆 expander 时用"""

    strategy: str
    expanded_query: str
    step_back_question: Optional[str] = None
    step_back_answer: Optional[str] = None
    hypothetical_doc: Optional[str] = None
