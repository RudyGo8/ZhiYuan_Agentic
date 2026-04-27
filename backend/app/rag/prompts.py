'''
@create_time: 2026/4/27 下午3:58
@Author: GeChao
@File: prompts.py
'''


GRADE_PROMPT = (
    "You are a grader assessing relevance of a retrieved document to a user question. \n "
    "Here is the retrieved document: \n\n {context} \n\n"
    "Here is the user question: {question} \n"
    "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
    "Return valid JSON only. Return a JSON object with a single field 'binary_score' containing 'yes' or 'no'.\n"

)


REWRITE_STRATEGY_PROMPT = """
你是一个 RAG 查询重写策略选择器。

请根据用户问题选择最合适的查询扩展策略：

- step_back：问题包含具体名称、代码、日期、术语，需要先抽象成更通用的问题。
- hyde：问题较模糊、概念性强，适合生成假设性答案文档辅助检索。
- complex：问题较复杂，需要综合 Step-back 和 HyDE。

用户问题：
{question}

只返回 JSON：
{{
  "strategy": "step_back" | "hyde" | "complex"
}}
"""