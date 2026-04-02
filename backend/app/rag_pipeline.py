"""
RAG Pipeline 模块 - 检索增强生成流程
================================================================================
核心流程 (使用 LangGraph 实现状态机):
    
    ┌────────────────┐    ┌──────────────┐    ┌──────────────────────────┐
    │  用户问题      │───▶│ retrieve_    │───▶│  grade_documents        │
    │               │    │ initial      │    │  (相关性评估)            │
    │               │    │ (初始检索)    │    └───────────┬────────────┘
    └────────────────┘    └──────────────┘                │
                            │                             │
                            │ 文档相关                     │ 文档不相关
                            ▼                             ▼
                    ┌───────────────┐          ┌──────────────────────┐
                    │  生成答案     │          │ rewrite_question    │
                    │ (END)        │          │ (查询重写)           │
                    └───────────────┘          └──────────┬───────────┘
                                                          │
                                                          ▼
                                                  ┌──────────────────┐
                                                  │ retrieve_expanded│
                                                  │ (扩展检索)       │
                                                  └────────┬─────────┘
                                                           │
                                                           ▼
                                                    ┌───────────┐
                                                    │   END    │
                                                    └───────────┘
    
关键特性:
    1. 三级检索: Leaf/Parent/Higher Level 分块
    2. Hybrid Search: 密集向量 + 稀疏向量 RRF 融合
    3. Auto-merging: 自动合并父分块
    4. Re-rank: 外部重排序模型
    5. 查询重写: step-back / HyDE / complex 策略
================================================================================
"""
from typing import Literal, TypedDict, List, Optional
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.rag_utils import retrieve_documents, step_back_expand, generate_hypothetical_document
from app.tools import emit_rag_step

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")
GRADE_MODEL = os.getenv("GRADE_MODEL", "qwen-plus")

_grader_model = None  # 相关性评估模型 (LLM)
_router_model = None  # 查询重写模型 (LLM)


def _get_grader_model():
    # Lazily initialize relevance-grader model and cache it in-process.
    """获取相关性评估模型"""
    global _grader_model
    if not API_KEY or not GRADE_MODEL:
        return None
    if _grader_model is None:
        _grader_model = init_chat_model(
            model=GRADE_MODEL,
            model_provider="openai",
            api_key=API_KEY,
            base_url=BASE_URL,
            temperature=0,
            stream_usage=True,
        )
    return _grader_model


def _get_router_model():
    # Lazily initialize rewrite-strategy router model and cache it.
    """获取查询重写模型"""
    global _router_model
    if not API_KEY or not MODEL:
        return None
    if _router_model is None:
        _router_model = init_chat_model(
            model=MODEL,
            model_provider="openai",
            api_key=API_KEY,
            base_url=BASE_URL,
            temperature=0,
            stream_usage=True,
        )
    return _router_model


# ===============================================================================
# 提示词模板
# ===============================================================================
GRADE_PROMPT = (
    "You are a grader assessing relevance of a retrieved document to a user question. \n "
    "Here is the retrieved document: \n\n {context} \n\n"
    "Here is the user question: {question} \n"
    "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
    "Return valid JSON only. Return a JSON object with a single field 'binary_score' containing 'yes' or 'no'.\n"

)


class GradeDocuments(BaseModel):
    """相关性评估输出结构"""
    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )


class RewriteStrategy(BaseModel):
    """查询重写策略输出结构"""
    strategy: Literal["step_back", "hyde", "complex"]


# RAG 状态定义
class RAGState(TypedDict):
    """
    RAG Pipeline 状态定义
    
    字段说明:
        - question: 原始用户问题
        - query: 当前查询 (可能是重写后的)
        - context: 格式化后的文档上下文
        - docs: 检索到的文档列表
        - route: 当前路由 (generate_answer / rewrite_question)
        - expansion_type: 扩展策略类型
        - expanded_query: 扩展后的查询
        - step_back_question: 退步问题
        - step_back_answer: 退步答案
        - hypothetical_doc: HyDE 假设文档
        - rag_trace: 执行元数据
    """
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


def _format_docs(docs: List[dict]) -> str:
    if not docs:
        return ""
    chunks = []
    for i, doc in enumerate(docs, 1):
        source = doc.get("filename", "Unknown")
        page = doc.get("page_number", "N/A")
        text = doc.get("text", "")
        chunks.append(f"[{i}] {source} (Page {page}):\n{text}")
    return "\n\n---\n\n".join(chunks)


# ===============================================================================
# [节点1] retrieve_initial - 初始检索
# ===============================================================================
def retrieve_initial(state: RAGState) -> RAGState:

    query = state["question"]
    emit_rag_step("🔍", "正在检索知识库...", f"查询: {query[:50]}")

    # 调用底层检索函数 (见 rag_utils.py)
    retrieved = retrieve_documents(query, top_k=5)
    results = retrieved.get("docs", [])
    retrieve_meta = retrieved.get("meta", {})
    context = _format_docs(results)

    # ============================================================================
    # RAG Step 2: 三级分块检索 (Auto-merging)
    # ============================================================================
    # 发送步骤更新 (流式输出用)
    emit_rag_step(
        "🧱",
        "三级分块检索",
        (
            f"叶子层 L{retrieve_meta.get('leaf_retrieve_level', 3)} 召回，"
            f"候选 {retrieve_meta.get('candidate_k', 0)}"
        ),
    )
    emit_rag_step(
        "🧩",
        "Auto-merging 合并",
        (
            f"启用: {bool(retrieve_meta.get('auto_merge_enabled'))}，"
            f"应用: {bool(retrieve_meta.get('auto_merge_applied'))}，"
            f"替换片段: {retrieve_meta.get('auto_merge_replaced_chunks', 0)}"
        ),
    )
    emit_rag_step("✅", f"检索完成，找到 {len(results)} 个片段", f"模式: {retrieve_meta.get('retrieval_mode', 'hybrid')}")

    # ============================================================================
    # RAG Step 3: 构建 RAG 执行追踪数据
    # ============================================================================
    rag_trace = {
        "tool_used": True,
        "tool_name": "search_knowledge_base",
        "query": query,
        "expanded_query": query,
        "retrieved_chunks": results,
        "initial_retrieved_chunks": results,
        "retrieval_stage": "initial",
        "rerank_enabled": retrieve_meta.get("rerank_enabled"),
        "rerank_applied": retrieve_meta.get("rerank_applied"),
        "rerank_model": retrieve_meta.get("rerank_model"),
        "rerank_endpoint": retrieve_meta.get("rerank_endpoint"),
        "rerank_error": retrieve_meta.get("rerank_error"),
        "retrieval_mode": retrieve_meta.get("retrieval_mode"),
        "candidate_k": retrieve_meta.get("candidate_k"),
        "leaf_retrieve_level": retrieve_meta.get("leaf_retrieve_level"),
        "auto_merge_enabled": retrieve_meta.get("auto_merge_enabled"),
        "auto_merge_applied": retrieve_meta.get("auto_merge_applied"),
        "auto_merge_threshold": retrieve_meta.get("auto_merge_threshold"),
        "auto_merge_replaced_chunks": retrieve_meta.get("auto_merge_replaced_chunks"),
        "auto_merge_steps": retrieve_meta.get("auto_merge_steps"),
    }
    return {
        "query": query,
        "docs": results,
        "context": context,
        "rag_trace": rag_trace,
    }


# ===============================================================================
# [节点2] grade_documents_node - 相关性评估
# ===============================================================================
def grade_documents_node(state: RAGState) -> RAGState:
    # Decide whether current retrieval is good enough to answer directly.
    """
    ================================================================================
    [LangGraph 节点2] 相关性评估 - grade_documents_node
    ================================================================================
    功能: 使用 LLM 评估检索到的文档与用户问题的相关性
    
    流程:
        1. 构建评估 Prompt
        2. 调用 LLM (Grade Model) 进行相关性评分
        3. 根据评分决定路由:
           - yes → generate_answer (文档相关，直接生成答案)
           - no → rewrite_question (文档不相关，重写查询)
    
    评估标准:
        - 文档是否包含与问题相关的关键词?
        - 文档的语义是否与问题相关?
    ================================================================================
    """
    # ============================================================================
    # RAG Step 4: LLM 相关性评估
    # ============================================================================
    grader = _get_grader_model()
    emit_rag_step("📊", "正在评估文档相关性...")

    # 如果没有配置 Grading Model，默认重写查询
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

    # 构建评估 Prompt
    prompt = GRADE_PROMPT.format(question=question, context=context)

    # 调用 LLM 进行相关性评估
    response = grader.with_structured_output(GradeDocuments).invoke(
        [{"role": "user", "content": prompt}]
    )

    score = (response.binary_score or "").strip().lower()

    # ============================================================================
    # RAG Step 5: 路由决策
    # ============================================================================
    # 路由决策: yes → 生成答案, no → 重写查询
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


# ===============================================================================
# [节点3] rewrite_question_node - 查询重写
# ===============================================================================
def rewrite_question_node(state: RAGState) -> RAGState:
    # Produce expanded query when initial retrieval quality is insufficient.
    """
    ================================================================================
    [LangGraph 节点3] 查询重写 - rewrite_question_node
    ================================================================================
    功能: 当首次检索结果不相关时，对查询进行重写和扩展
    
    重写策略 (由 LLM 选择):
        1. step_back (退步问题)
           - 适用: 包含具体名称、日期、代码等细节的问题
           - 原理: 先理解通用概念，再回到具体问题
           - 示例: "Transformer注意力机制" → "什么是Transformer?" + "注意力机制原理"
        
        2. hyde (假设性文档)
           - 适用: 模糊、概念性、需要解释的问题
           - 原理: 先让 LLM 生成假设性回答，再用它检索
           - 示例: "机器学习是什么?" → 生成假设回答 → 用假设回答检索
        
        3. complex (综合)
           - 适用: 多步骤、需要分解或综合的问题
           - 原理: 同时使用 step_back 和 hyde
    
    输出字段:
        - expansion_type: 使用的策略
        - expanded_query: 扩展后的查询
        - step_back_question: 退步问题
        - step_back_answer: 退步答案
        - hypothetical_doc: HyDE 假设文档
    ================================================================================
    """
    # ============================================================================
    # RAG Step 6: 选择查询重写策略
    # ============================================================================
    question = state["question"]
    emit_rag_step("✏️", "正在重写查询...")
    router = _get_router_model()

    # 策略选择 (默认 step_back)
    strategy = "step_back"
    if router:
        prompt = (
            "请根据用户问题选择最合适的查询扩展策略，仅输出策略名。\n"
            "- step_back：包含具体名称、日期、代码等细节，需要先理解通用概念的问题。\n"
            "- hyde：模糊、概念性、需要解释或定义的问题。\n"
            "- complex：多步骤、需要分解或综合多种信息的复杂问题。\n"
            f"用户问题：{question}\n"
            "返回一个JSON对象，其中包含一个字段'strategy'，值为'step_back'、'hyde'或'complex'。"
        )
        try:
            decision = router.with_structured_output(RewriteStrategy).invoke(
                [{"role": "user", "content": prompt}]
            )
            strategy = decision.strategy
        except Exception:
            strategy = "step_back"

    expanded_query = question
    step_back_question = ""
    step_back_answer = ""
    hypothetical_doc = ""

    # ============================================================================
    # RAG Step 7: 执行 step_back 策略
    # ============================================================================
    # 执行 step_back 策略
    if strategy in ("step_back", "complex"):
        emit_rag_step("🧠", f"使用策略: {strategy}", "生成退步问题")
        step_back = step_back_expand(question)
        step_back_question = step_back.get("step_back_question", "")
        step_back_answer = step_back.get("step_back_answer", "")
        expanded_query = step_back.get("expanded_query", question)

    # ============================================================================
    # RAG Step 8: 执行 HyDE 策略
    # ============================================================================
    # 执行 HyDE 策略
    if strategy in ("hyde", "complex"):
        emit_rag_step("📝", "HyDE 假设性文档生成中...")
        hypothetical_doc = generate_hypothetical_document(question)

    rag_trace = state.get("rag_trace", {}) or {}
    rag_trace.update({
        "rewrite_strategy": strategy,
        "rewrite_query": expanded_query,
    })

    return {
        "expansion_type": strategy,
        "expanded_query": expanded_query,
        "step_back_question": step_back_question,
        "step_back_answer": step_back_answer,
        "hypothetical_doc": hypothetical_doc,
        "rag_trace": rag_trace,
    }


# ===============================================================================
# [节点4] retrieve_expanded - 扩展检索
# ===============================================================================
def retrieve_expanded(state: RAGState) -> RAGState:
    # Second retrieval pass using selected expansion strategy.
    """
    ================================================================================
    [LangGraph 节点4] 扩展检索 - retrieve_expanded
    ================================================================================
    功能: 使用重写后的查询进行二次检索
    
    检索策略:
        - 根据 rewrite_question_node 选择的策略执行:
          - hyde: 使用假设性文档检索
          - step_back: 使用退步问题检索
          - complex: 同时使用两者
        
        - 多策略结果融合 (RRF)
        
        - 去重处理
    
    输出字段:
        - docs: 扩展检索后的文档列表
        - context: 格式化后的文档字符串
        - rag_trace: 更新后的执行元数据
    ================================================================================
    """
    # ============================================================================
    # RAG Step 9: 使用重写后的查询进行扩展检索
    # ============================================================================
    strategy = state.get("expansion_type") or "step_back"
    emit_rag_step("🔄", "使用扩展查询重新检索...", f"策略: {strategy}")

    results: List[dict] = []
    rerank_applied_any = False
    rerank_enabled_any = False
    rerank_model = None
    rerank_endpoint = None
    rerank_errors = []
    retrieval_mode = None
    candidate_k = None
    leaf_retrieve_level = None
    auto_merge_enabled = None
    auto_merge_applied = False
    auto_merge_threshold = None
    auto_merge_replaced_chunks = 0
    auto_merge_steps = 0

    # ============================================================================
    # RAG Step 10: HyDE 检索 (如果启用)
    # ============================================================================
    # ========== HyDE 检索 ==========
    if strategy in ("hyde", "complex"):
        hypothetical_doc = state.get("hypothetical_doc") or generate_hypothetical_document(state["question"])
        retrieved_hyde = retrieve_documents(hypothetical_doc, top_k=5)
        results.extend(retrieved_hyde.get("docs", []))
        hyde_meta = retrieved_hyde.get("meta", {})
        emit_rag_step(
            "🧱",
            "HyDE 三级检索",
            (
                f"L{hyde_meta.get('leaf_retrieve_level', 3)} 召回，"
                f"候选 {hyde_meta.get('candidate_k', 0)}，"
                f"合并替换 {hyde_meta.get('auto_merge_replaced_chunks', 0)}"
            ),
        )
        rerank_applied_any = rerank_applied_any or bool(hyde_meta.get("rerank_applied"))
        rerank_enabled_any = rerank_enabled_any or bool(hyde_meta.get("rerank_enabled"))
        rerank_model = rerank_model or hyde_meta.get("rerank_model")
        rerank_endpoint = rerank_endpoint or hyde_meta.get("rerank_endpoint")
        if hyde_meta.get("rerank_error"):
            rerank_errors.append(f"hyde:{hyde_meta.get('rerank_error')}")
        retrieval_mode = retrieval_mode or hyde_meta.get("retrieval_mode")
        candidate_k = candidate_k or hyde_meta.get("candidate_k")
        leaf_retrieve_level = leaf_retrieve_level or hyde_meta.get("leaf_retrieve_level")
        auto_merge_enabled = auto_merge_enabled if auto_merge_enabled is not None else hyde_meta.get("auto_merge_enabled")
        auto_merge_applied = auto_merge_applied or bool(hyde_meta.get("auto_merge_applied"))
        auto_merge_threshold = auto_merge_threshold or hyde_meta.get("auto_merge_threshold")
        auto_merge_replaced_chunks += int(hyde_meta.get("auto_merge_replaced_chunks") or 0)
        auto_merge_steps += int(hyde_meta.get("auto_merge_steps") or 0)

    # ============================================================================
    # RAG Step 11: Step-back 检索 (如果启用)
    # ============================================================================
    # ========== Step-back 检索 ==========
    if strategy in ("step_back", "complex"):
        expanded_query = state.get("expanded_query") or state["question"]
        retrieved_stepback = retrieve_documents(expanded_query, top_k=5)
        results.extend(retrieved_stepback.get("docs", []))
        step_meta = retrieved_stepback.get("meta", {})
        emit_rag_step(
            "🧱",
            "Step-back 三级检索",
            (
                f"L{step_meta.get('leaf_retrieve_level', 3)} 召回，"
                f"候选 {step_meta.get('candidate_k', 0)}，"
                f"合并替换 {step_meta.get('auto_merge_replaced_chunks', 0)}"
            ),
        )
        rerank_applied_any = rerank_applied_any or bool(step_meta.get("rerank_applied"))
        rerank_enabled_any = rerank_enabled_any or bool(step_meta.get("rerank_enabled"))
        rerank_model = rerank_model or step_meta.get("rerank_model")
        rerank_endpoint = rerank_endpoint or step_meta.get("rerank_endpoint")
        if step_meta.get("rerank_error"):
            rerank_errors.append(f"step_back:{step_meta.get('rerank_error')}")
        retrieval_mode = retrieval_mode or step_meta.get("retrieval_mode")
        candidate_k = candidate_k or step_meta.get("candidate_k")
        leaf_retrieve_level = leaf_retrieve_level or step_meta.get("leaf_retrieve_level")
        auto_merge_enabled = auto_merge_enabled if auto_merge_enabled is not None else step_meta.get("auto_merge_enabled")
        auto_merge_applied = auto_merge_applied or bool(step_meta.get("auto_merge_applied"))
        auto_merge_threshold = auto_merge_threshold or step_meta.get("auto_merge_threshold")
        auto_merge_replaced_chunks += int(step_meta.get("auto_merge_replaced_chunks") or 0)
        auto_merge_steps += int(step_meta.get("auto_merge_steps") or 0)

    # ============================================================================
    # RAG Step 12: RRF 融合 + 去重
    # ============================================================================
    # ========== RRF 融合 + 去重 ==========
    deduped = []
    seen = set()
    for item in results:
        key = (item.get("filename"), item.get("page_number"), item.get("text"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    for idx, item in enumerate(deduped, 1):
        item["rrf_rank"] = idx

    context = _format_docs(deduped)
    emit_rag_step("✅", f"扩展检索完成，共 {len(deduped)} 个片段")
    rag_trace = state.get("rag_trace", {}) or {}
    rag_trace.update({
        "expanded_query": state.get("expanded_query") or state["question"],
        "step_back_question": state.get("step_back_question", ""),
        "step_back_answer": state.get("step_back_answer", ""),
        "hypothetical_doc": state.get("hypothetical_doc", ""),
        "expansion_type": strategy,
        "retrieved_chunks": deduped,
        "expanded_retrieved_chunks": deduped,
        "retrieval_stage": "expanded",
        "rerank_enabled": rerank_enabled_any,
        "rerank_applied": rerank_applied_any,
        "rerank_model": rerank_model,
        "rerank_endpoint": rerank_endpoint,
        "rerank_error": "; ".join(rerank_errors) if rerank_errors else None,
        "retrieval_mode": retrieval_mode,
        "candidate_k": candidate_k,
        "leaf_retrieve_level": leaf_retrieve_level,
        "auto_merge_enabled": auto_merge_enabled,
        "auto_merge_applied": auto_merge_applied,
        "auto_merge_threshold": auto_merge_threshold,
        "auto_merge_replaced_chunks": auto_merge_replaced_chunks,
        "auto_merge_steps": auto_merge_steps,
    })
    return {"docs": deduped, "context": context, "rag_trace": rag_trace}


# 构建 LangGraph 状态图

def build_rag_graph():
    # 图流程

    graph = StateGraph(RAGState)
    graph.add_node("retrieve_initial", retrieve_initial)
    graph.add_node("grade_documents", grade_documents_node)
    graph.add_node("rewrite_question", rewrite_question_node)
    graph.add_node("retrieve_expanded", retrieve_expanded)

    graph.set_entry_point("retrieve_initial")
    graph.add_edge("retrieve_initial", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        lambda state: state.get("route"),
        {
            "generate_answer": END,
            "rewrite_question": "rewrite_question",
        },
    )
    graph.add_edge("rewrite_question", "retrieve_expanded")
    graph.add_edge("retrieve_expanded", END)
    return graph.compile()


rag_graph = build_rag_graph()


def run_rag_graph(question: str) -> dict:
    # Public execution entrypoint used by search_knowledge_base tool.

    return rag_graph.invoke({
        "question": question,
        "query": question,
        "context": "",
        "docs": [],
        "route": None,
        "expansion_type": None,
        "expanded_query": None,
        "step_back_question": None,
        "step_back_answer": None,
        "hypothetical_doc": None,
        "rag_trace": None,
    })
