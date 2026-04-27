import os

from dotenv import load_dotenv

from app.config import logger
from app.mcp.client_manager import mcp_client_manager
from app.skills.router import build_skill_prompt
from app.tools import emit_rag_step

load_dotenv()

MCP_PREFETCH_MAX_SOURCES = max(1, int(os.getenv("MCP_PREFETCH_MAX_SOURCES", "2")))
MCP_PREFETCH_MAX_TOOLS_PER_SOURCE = max(1, int(os.getenv("MCP_PREFETCH_MAX_TOOLS_PER_SOURCE", "1")))
MANDATORY_RAG_TOOL_INSTRUCTION = (
    "执行约束：本轮回答前必须先调用一次 search_knowledge_base（RAG 检索）；"
    "若返回 TOOL_CALL_LIMIT_REACHED 或无相关结果，不要重复调用，"
    "直接基于现有信息给出结论并简要说明限制。"
)


def _append_mandatory_rag_instruction(skill_prompt: str) -> str:
    content = (skill_prompt or "").rstrip()
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
        return "【外部实时信息】未获取到可用结果。若结论依赖实时数据，请明确说明数据不足。", sources

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
    skill_prompt = build_skill_prompt(user_text, plan)
    prefetched_sources: list[str] = []
    try:
        prefetched_context, prefetched_sources = _prefetch_mcp_context(user_text, plan)
    except Exception as exc:
        logger.warning("mcp_context_prefetch_failed user_id=%s err=%s", user_id, exc)
        prefetched_context = ""
        prefetched_sources = []

    if prefetched_context:
        skill_prompt = f"{skill_prompt}\n\n{prefetched_context}"
    if plan.require_rag:
        skill_prompt = _append_mandatory_rag_instruction(skill_prompt)
    return skill_prompt, prefetched_sources
