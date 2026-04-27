import os

from dotenv import load_dotenv

from app.config import logger
from app.mcp.client_manager import mcp_client_manager

from app.tools import emit_rag_step

load_dotenv()

MCP_PREFETCH_MAX_SOURCES = max(1, int(os.getenv("MCP_PREFETCH_MAX_SOURCES", "2")))
MCP_PREFETCH_MAX_TOOLS_PER_SOURCE = max(1, int(os.getenv("MCP_PREFETCH_MAX_TOOLS_PER_SOURCE", "1")))
MANDATORY_RAG_TOOL_INSTRUCTION = (
    "Mandatory RAG instruction:\n"
    "You must call the search_knowledge_base tool once before answering this turn.\n"
    "If the tool returns TOOL_CALL_LIMIT_REACHED or no relevant evidence, do not call it repeatedly.\n"
    "In that case, answer based on the available evidence and clearly state the limitation.\n"
    "Do not answer from model memory when knowledge-base evidence is required."
)


def _append_mandatory_rag_instruction(turn_prompt: str) -> str:
    content = (turn_prompt or "").rstrip()
    if MANDATORY_RAG_TOOL_INSTRUCTION in content:
        return content
    if not content:
        return MANDATORY_RAG_TOOL_INSTRUCTION
    return f"{content}\n\n{MANDATORY_RAG_TOOL_INSTRUCTION}"


def _select_mcp_prefetch_sources(user_text: str, plan) -> list[str]:
    configured_sources = [
        str(source).strip().lower()
        for source in (getattr(plan, "mcp_sources", []) or [])
        if str(source).strip()
    ]
    if not configured_sources:
        return []
    return configured_sources[:MCP_PREFETCH_MAX_SOURCES]


def _prefetch_mcp_context(user_text: str, plan) -> tuple[str, list[str]]:
    if not getattr(plan, "use_mcp", False):
        return "", []
    sources = _select_mcp_prefetch_sources(user_text, plan)
    if not sources:
        return "", []
    if not mcp_client_manager.enabled:
        return "", sources

    query = (user_text or "").strip()
    all_items: list[dict] = []
    for source in sources:
        emit_rag_step("🔎", f"查询外部来源: {source}", query[:80])
        all_items.extend(
            mcp_client_manager.query_source(
                source,
                query,
                max_tools=MCP_PREFETCH_MAX_TOOLS_PER_SOURCE,
            )
        )

    if not all_items:
        return (
            "【外部实时信息】未获取到可用结果。"
            "如果结论依赖实时数据，必须明确说明当前实时证据不足，不要编造。"
        ), sources

    lines = ["【实时信息】"]
    for idx, item in enumerate(all_items[:8], 1):
        source = item.get("source", "unknown")
        tool_name = item.get("tool_name", "unknown")
        summary = (item.get("summary") or "").replace("\n", " ").strip()
        if len(summary) > 280:
            summary = summary[:280] + "..."
        lines.append(f"{idx}. source={source}, tool={tool_name}, summary={summary}")
    lines.append("请优先基于以上信息输出结论；若信息已足够，请不要重复调用相同外部来源。")
    return "\n".join(lines), sources


def build_turn_prompt(user_text: str, plan, user_id: str) -> tuple[str, list[str]]:
    turn_prompt = build_plan_prompt(user_text, plan)
    prefetched_sources: list[str] = []
    try:
        prefetched_context, prefetched_sources = _prefetch_mcp_context(user_text, plan)
    except Exception as exc:
        logger.warning("mcp_context_prefetch_failed user_id=%s err=%s", user_id, exc)
        prefetched_context = ""
        prefetched_sources = []

    if prefetched_context:
        turn_prompt = f"{turn_prompt}\n\n{prefetched_context}"
    if getattr(plan, "require_rag", False):
        turn_prompt = _append_mandatory_rag_instruction(turn_prompt)
    return turn_prompt, prefetched_sources


def build_plan_prompt(user_text: str, plan) -> str:
    lines = [
        "You are a Plan-driven Agentic RAG assistant.",
        "Follow the runtime policy strictly.",
        "Use only the allowed tools for this turn.",
        "Do not fabricate facts, tool results, citations, business rules, or system behavior.",
        "",
        "业务场景：",
        "你主要服务于中文用户，应用场景包括跨境电商、跨境物流、订单异常诊断、售后处理、平台规则问答、ERP 操作指导。",
        "最终回答必须使用中文，表达要简洁、准确、可执行。",
        "",
        f"用户问题：{user_text}",
    ]

    allowed_tools = getattr(plan, "allowed_tools", []) or []

    if allowed_tools:
        lines.append(f"Allowed tools: {', '.join(allowed_tools)}")

    if getattr(plan, "require_rag", False):
        lines.extend([
            "",
            "RAG requirement:",
            "You must call search_knowledge_base before answering this question.",
            "Answer only based on retrieved knowledge-base evidence.",
            "If no relevant evidence is found, say that the knowledge base does not contain enough information.",
        ])

    if getattr(plan, "use_mcp", False):
        lines.extend([
            "",
            "MCP requirement:",
            "You may use MCP tools to retrieve external real-time context.",
            "Prefer tool evidence over model memory.",
        ])

    lines.append("If tool evidence is insufficient, clearly state that the available evidence is insufficient. Do not fabricate.")
    lines.append("最终回答必须使用中文说明证据不足的原因。")

    return "\n".join(lines)
