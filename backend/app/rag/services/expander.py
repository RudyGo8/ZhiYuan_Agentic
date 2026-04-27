'''
@create_time: 2026/4/27 下午4:01
@Author: GeChao
@File: expander.py
'''
import json
import re

from app.rag.models import _get_default_model


def step_back_expand(query: str) -> dict:
    try:
        from langchain.chat_models import init_chat_model
        model = _get_default_model()

        prompt = f"""请根据用户问题生成一个更通用的退步问题（Step-back），以及对应的通用答案。
用户问题：{query}

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "step_back_question": "更通用的退步问题",
    "step_back_answer": "通用答案",
    "expanded_query": "可用于检索的扩展查询"
}}"""

        response = model.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "step_back_question": result.get("step_back_question", query),
                "step_back_answer": result.get("step_back_answer", ""),
                "expanded_query": result.get("expanded_query", query)
            }
    except Exception as e:
        pass

    return {
        "step_back_question": query,
        "step_back_answer": "",
        "expanded_query": query
    }


# 假设文档生成策略
def generate_hypothetical_document(query: str) -> str:
    try:
        from langchain.chat_models import init_chat_model
        model = _get_default_model()

        prompt = f"""
请生成一个假设性的文档内容，用于HyDE检索。
这个文档应该回答以下问题：{query}
请直接生成文档内容，不要添加解释。"""

        response = model.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception:
        return query