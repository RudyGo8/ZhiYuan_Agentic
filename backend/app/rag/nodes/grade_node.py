'''
@create_time: 2026/4/27 下午3:59
@Author: GeChao
@File: grade_node.py
'''
from app.rag.models import _get_grader_model
from app.rag.prompts import GRADE_PROMPT
from app.rag.schema import GradeDocuments
from app.rag.state import RAGState
from app.tools.runtime import emit_rag_step


# 相关性评估
def grade_documents_node(state: RAGState) -> RAGState:
    grader = _get_grader_model()
    emit_rag_step("📊", "正在评估文档相关性...")

    # 如果未配置评估模型，默认进入查询重写
    if not grader:
        grade_update = {
            "grade_score": "unknown",
            "grade_route": "rewrite_question",
            "rewrite_needed": True,
        }
        rag_trace = state.get("rag_trace", {}) or {}
        rag_trace.update(grade_update)
        return {"route": "rewrite_question", "rag_trace": rag_trace}

    question = state["question"]
    context = state.get("context", "")

    prompt = GRADE_PROMPT.format(question=question, context=context)

    # 调用大模型做相关性评估
    response = grader.with_structured_output(GradeDocuments).invoke(
        [{"role": "user", "content": prompt}]
    )
    score = (response.binary_score or "").strip().lower()

    # 路由决策：yes 直接回答，no 重写查询
    route = "generate_answer" if score == "yes" else "rewrite_question"

    if route == "generate_answer":
        emit_rag_step("✅", "文档相关性评估通过", f"评分: {score}")
    else:
        emit_rag_step("⚠️", "文档相关性不足，将重写查询", f"评分: {score}")

    grade_update = {
        "grade_score": score,
        "grade_route": route,
        "rewrite_needed": route == "rewrite_question",
    }
    rag_trace = state.get("rag_trace", {}) or {}
    rag_trace.update(grade_update)

    return {"route": route, "rag_trace": rag_trace}