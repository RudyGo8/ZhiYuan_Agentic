from dotenv import load_dotenv
import os
import json
import asyncio
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from app.tools import (
    emit_rag_step,
    get_current_weather,
    search_knowledge_base,
    get_last_rag_context,
    reset_tool_call_guards,
    set_rag_step_queue,
)
from app.config import logger
from app.mcp.agent_tools import get_enabled_mcp_tools
from app.mcp.client_manager import mcp_client_manager
from app.mcp.policy import reset_turn_policy, set_turn_policy
from app.mcp.trace import get_mcp_trace, reset_mcp_trace
from app.skills.router import build_skill_prompt, route_skill
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")
MODEL_INPUT_PRICE_PER_1K = float(os.getenv("MODEL_INPUT_PRICE_PER_1K", "0"))
MODEL_OUTPUT_PRICE_PER_1K = float(os.getenv("MODEL_OUTPUT_PRICE_PER_1K", "0"))
COST_CURRENCY = os.getenv("COST_CURRENCY", "CNY")
AGENT_RECURSION_LIMIT = max(8, int(os.getenv("AGENT_RECURSION_LIMIT", "16")))
MCP_PREFETCH_MAX_SOURCES = max(1, int(os.getenv("MCP_PREFETCH_MAX_SOURCES", "2")))
MCP_PREFETCH_MIN_QUERY_CHARS = max(1, int(os.getenv("MCP_PREFETCH_MIN_QUERY_CHARS", "2")))
MCP_PREFETCH_MAX_TOOLS_PER_SOURCE = max(1, int(os.getenv("MCP_PREFETCH_MAX_TOOLS_PER_SOURCE", "1")))

MCP_SOURCE_HINTS = {
    "monitor": (
        "故障", "报错", "错误", "异常", "告警", "超时", "状态", "可用性", "延迟", "监控",
        "error", "incident", "alert", "latency", "status", "monitor", "availability",
    ),
    "git": (
        "代码", "提交", "变更", "上线", "发布", "回滚", "分支", "pr", "commit",
        "git", "github", "gitlab", "merge", "release",
    ),
    "docs": (
        "文档", "方案", "设计", "说明", "wiki", "纪要", "手册", "readme", "spec", "doc", "document",
    ),
}

MCP_SKILL_SOURCE_PRIORITIES = {
    "troubleshooting": ("monitor", "git"),
    "test_analysis": ("git", "docs"),
    "doc_analysis": ("docs",),
    "default_rag": ("monitor", "docs"),
}


def _normalize_usage(usage: dict | None) -> dict | None:
    if not isinstance(usage, dict):
        return None
    in_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
    out_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
    total_tokens = usage.get("total_tokens", 0) or (in_tokens + out_tokens)
    return {
        "input_tokens": int(in_tokens),
        "output_tokens": int(out_tokens),
        "total_tokens": int(total_tokens),
    }


def _extract_usage_from_message(msg) -> dict | None:
    if msg is None:
        return None
    usage = getattr(msg, "usage_metadata", None)
    normalized = _normalize_usage(usage)
    if normalized:
        return normalized
    response_meta = getattr(msg, "response_metadata", None) or {}
    if isinstance(response_meta, dict):
        normalized = _normalize_usage(response_meta.get("token_usage"))
        if normalized:
            return normalized
    return None


def _estimate_cost(usage: dict | None) -> dict:
    if not usage:
        return {"model": MODEL, "usage": None}
    return {
        "model": MODEL,
        "usage": usage,
    }


def _build_mcp_summary(mcp_calls: list[dict] | None) -> dict:
    calls = mcp_calls or []
    total = len(calls)
    success = sum(1 for item in calls if isinstance(item, dict) and item.get("success") is True)
    failed = max(0, total - success)
    sources = sorted(
        {
            str(item.get("server_name")).strip()
            for item in calls
            if isinstance(item, dict) and item.get("server_name")
        }
    )
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "sources": sources,
    }


class ConversationStorage:

    @staticmethod
    def _messages_cache_key(user_id: str, session_id: str) -> str:
        return f"chat_messages:{user_id}:{session_id}"

    @staticmethod
    def _sessions_cache_key(user_id: str) -> str:
        return f"chat_sessions:{user_id}"

    @staticmethod
    def _to_langchain_messages(records: list[dict]) -> list:
        messages = []
        for msg_data in records:
            msg_type = msg_data.get("type")
            content = msg_data.get("content", "")
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content))
            elif msg_type == "system":
                messages.append(SystemMessage(content=content))
        return messages

    def save(self, user_id: str, session_id: str, messages: list, metadata: dict = None, extra_message_data: list = None):

        from app.cache import cache
        from app.database import SessionLocal
        from app.models.db_user import User
        from app.models.db_chat_session import ChatSession
        from app.models.db_chat_message import ChatMessage

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return

            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                session = ChatSession(user_id=user.id, session_id=session_id, metadata_json=metadata or {})
                db.add(session)
                db.flush()
            else:
                session.metadata_json = metadata or {}

            db.query(ChatMessage).filter(ChatMessage.session_ref_id == session.id).delete(synchronize_session=False)

            now = datetime.now()
            for idx, msg in enumerate(messages):
                rag_trace = None
                if extra_message_data and idx < len(extra_message_data):
                    extra = extra_message_data[idx] or {}
                    rag_trace = extra.get("rag_trace")

                db.add(
                    ChatMessage(
                        session_ref_id=session.id,
                        message_type=msg.type,
                        content=str(msg.content),
                        rag_trace=rag_trace,
                    )
                )

            session.update_time = now
            db.commit()
            # Invalidate caches after successful write to avoid stale reads.
            cache.delete(self._messages_cache_key(user_id, session_id))
            cache.delete(self._sessions_cache_key(user_id))
        finally:
            db.close()

    def load(self, user_id: str, session_id: str) -> list:

        from app.cache import cache

        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return self._to_langchain_messages(cached)

        records = self.get_session_messages(user_id, session_id)
        return self._to_langchain_messages(records)

    def list_sessions(self, user_id: str) -> list:
        """List all session IDs for a user."""
        return [item["session_id"] for item in self.list_session_infos(user_id)]

    def list_session_infos(self, user_id: str) -> list[dict]:
        from app.cache import cache

        cached = cache.get_json(self._sessions_cache_key(user_id))
        if cached is not None:
            return cached

        from app.database import SessionLocal
        from app.models.db_user import User
        from app.models.db_chat_session import ChatSession
        from app.models.db_chat_message import ChatMessage

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []

            sessions = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id)
                .order_by(ChatSession.update_time.desc())
                .all()
            )
            result = []
            for s in sessions:
                count = db.query(ChatMessage).filter(ChatMessage.session_ref_id == s.id).count()
                result.append(
                    {
                        "session_id": s.session_id,
                        "updated_at": s.update_time.isoformat() if s.update_time else "",
                        "message_count": count,
                    }
                )
            cache.set_json(self._sessions_cache_key(user_id), result)
            return result
        finally:
            db.close()

    def get_session_messages(self, user_id: str, session_id: str) -> list[dict]:
        from app.cache import cache

        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return cached

        from app.database import SessionLocal
        from app.models.db_user import User
        from app.models.db_chat_session import ChatSession
        from app.models.db_chat_message import ChatMessage

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []
            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                return []

            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_ref_id == session.id)
                .order_by(ChatMessage.id.asc())
                .all()
            )
            result = [
                {
                    "type": row.message_type,
                    "content": row.content,
                    "timestamp": row.create_time.isoformat() if row.create_time else "",
                    "rag_trace": row.rag_trace,
                }
                for row in rows
            ]
            cache.set_json(self._messages_cache_key(user_id, session_id), result)
            return result
        finally:
            db.close()

    def delete_session(self, user_id: str, session_id: str) -> bool:

        from app.cache import cache
        from app.database import SessionLocal
        from app.models.db_user import User
        from app.models.db_chat_session import ChatSession

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return False
            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                return False

            db.delete(session)
            db.commit()
            cache.delete(self._messages_cache_key(user_id, session_id))
            cache.delete(self._sessions_cache_key(user_id))
            return True
        finally:
            db.close()


def create_agent_instance(extra_tools: list | None = None):
    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )

    tools = [get_current_weather, search_knowledge_base] + (extra_tools or [])
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "You are a helpful AI assistant named 知源 Assistant.You were developed by Rudy."
            "Use tools when needed for factual and grounded answers. "
            "For questions related to documents or knowledge base, call search_knowledge_base first, but at most once per turn. "
            "If search_knowledge_base returns TOOL_CALL_LIMIT_REACHED or no relevant documents, do not retry it; proceed with existing evidence. "
            "When the user needs latest status/change/alerts, you may call available MCP read-only tools. "
            "Avoid repeatedly calling the same MCP source unless new evidence is required. "
            "For weather questions, use get_current_weather tool. "
            "If evidence is insufficient, explicitly state limitations."
        ),
    )
    return agent, model


agent, model = create_agent_instance()
storage = ConversationStorage()


def rebuild_agent_with_external_tools() -> list[str]:
    global agent
    extra_tools = get_enabled_mcp_tools()
    agent, _ = create_agent_instance(extra_tools=extra_tools)
    return [getattr(item, "__name__", getattr(item, "name", "unknown")) for item in extra_tools]


def summarize_old_messages(model, messages: list) -> str:
    """Summarize old conversation turns to keep prompt length bounded."""
    old_conversation = "\n".join(
        [f"{'用户' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in messages]
    )

    summary_prompt = (
        "请总结以下对话关键信息（用户偏好、重要事实、待办事项）。\n\n"
        f"{old_conversation}\n\n"
        "请输出简洁摘要。"
    )

    summary = model.invoke(summary_prompt).content
    return summary


def _select_mcp_prefetch_sources(user_text: str, plan) -> list[str]:
    query = (user_text or "").strip().lower()
    configured_sources = [
        str(source).strip().lower()
        for source in (getattr(plan, "mcp_sources", []) or [])
        if str(source).strip()
    ]
    if not configured_sources:
        return []

    if len(query) < MCP_PREFETCH_MIN_QUERY_CHARS:
        return configured_sources[:1]

    priority_sources = set(MCP_SKILL_SOURCE_PRIORITIES.get(getattr(plan, "name", ""), ()))
    scored: list[tuple[int, int, str]] = []
    for idx, source in enumerate(configured_sources):
        hints = MCP_SOURCE_HINTS.get(source, ())
        score = sum(1 for kw in hints if kw in query)
        if source in priority_sources:
            score += 1
        scored.append((score, -idx, source))

    scored.sort(reverse=True)
    selected = [source for score, _, source in scored if score > 0]
    if not selected:
        prioritized = [source for source in MCP_SKILL_SOURCE_PRIORITIES.get(getattr(plan, "name", ""), ()) if source in configured_sources]
        selected = prioritized or configured_sources[:1]
    return selected[:MCP_PREFETCH_MAX_SOURCES]


def _prefetch_mcp_context(user_text: str, plan) -> tuple[str, list[str]]:
    """
    Prefetch MCP evidence for skill-mode turns.
    This avoids "template says queried MCP" while actual MCP calls are zero.
    """
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
        return "【外部实时证据】未获取到可用结果。若结论依赖实时数据，请明确说明证据不足。", sources

    lines = ["【外部实时证据】"]
    for idx, item in enumerate(all_items[:8], 1):
        source = item.get("source", "unknown")
        tool_name = item.get("tool_name", "unknown")
        summary = (item.get("summary") or "").replace("\n", " ").strip()
        if len(summary) > 280:
            summary = summary[:280] + "..."
        lines.append(f"{idx}. source={source}, tool={tool_name}, summary={summary}")
    lines.append("请优先基于以上证据输出结论；若证据已足够，请不要重复调用相同外部来源。")
    return "\n".join(lines), sources


def chat_with_agent(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
    messages = storage.load(user_id, session_id)
    plan = route_skill(user_text)
    set_turn_policy(plan.use_mcp, plan.mcp_sources)
    reset_mcp_trace()

    get_last_rag_context(clear=True)
    reset_tool_call_guards()

    try:
        if len(messages) > 50:
            summary = summarize_old_messages(model, messages[:40])

            messages = [
                           SystemMessage(content=f"之前的对话摘要：\n{summary}")
                       ] + messages[40:]

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
        if getattr(plan, "use_mcp", False):
            skill_prompt = (
                f"{skill_prompt}\n\n"
                "执行约束：优先调用一次 search_knowledge_base；若提示已达调用上限或无相关结果，不要重复调用，直接基于现有证据给结论。"
            )
        messages.append(HumanMessage(content=skill_prompt))

        result = agent.invoke(
            {"messages": messages},
            config={"recursion_limit": AGENT_RECURSION_LIMIT},
        )

        response_content = ""
        usage = None
        if isinstance(result, dict):
            if "output" in result:
                response_content = result["output"]
            elif "messages" in result and result["messages"]:
                msg = result["messages"][-1]
                response_content = getattr(msg, "content", str(msg))
                usage = _extract_usage_from_message(msg)
            else:
                response_content = str(result)
        elif hasattr(result, "content"):
            response_content = result.content
            usage = _extract_usage_from_message(result)
        else:
            response_content = str(result)

        messages.append(AIMessage(content=response_content))

        rag_context = get_last_rag_context(clear=True)
        rag_trace = rag_context.get("rag_trace") if rag_context else None
        if not isinstance(rag_trace, dict):
            rag_trace = {}
        mcp_calls = get_mcp_trace(clear=True)
        rag_trace["token_usage"] = _estimate_cost(usage)
        rag_trace["skill"] = plan.to_trace()
        rag_trace["mcp_calls"] = mcp_calls
        rag_trace["mcp_summary"] = _build_mcp_summary(mcp_calls)
        rag_trace["mcp_prefetch_sources"] = prefetched_sources
        rag_trace["mcp_used"] = bool(mcp_calls)

        extra_message_data = [None] * (len(messages) - 1) + [{"rag_trace": rag_trace}]
        storage.save(user_id, session_id, messages, extra_message_data=extra_message_data)

        return {
            "response": response_content,
            "rag_trace": rag_trace,
        }
    finally:
        reset_turn_policy()


# SSE流式输出
async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
    messages = storage.load(user_id, session_id)
    plan = route_skill(user_text)
    set_turn_policy(plan.use_mcp, plan.mcp_sources)
    reset_mcp_trace()

    get_last_rag_context(clear=True)
    reset_tool_call_guards()

    output_queue = asyncio.Queue()

    class _RagStepProxy:
        def put_nowait(self, step):
            output_queue.put_nowait({"type": "rag_step", "step": step})

    set_rag_step_queue(_RagStepProxy())

    if len(messages) > 50:
        summary = summarize_old_messages(model, messages[:40])
        messages = [SystemMessage(content=f"之前的对话摘要：\n{summary}")] + messages[40:]

    if getattr(plan, "use_mcp", False):
        # Emit an early event so frontend is not stuck waiting for first token
        # when MCP prefetch is slow.
        yield f"data: {json.dumps({'type': 'rag_step', 'step': {'icon': '⏳', 'label': '处理中', 'detail': '正在获取外部实时证据...'}})}\n\n"

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
    if getattr(plan, "use_mcp", False):
        skill_prompt = (
            f"{skill_prompt}\n\n"
            "执行约束：优先调用一次 search_knowledge_base；若提示已达调用上限或无相关结果，不要重复调用，直接基于现有证据给结论。"
        )
    messages.append(HumanMessage(content=skill_prompt))

    full_response = ""
    stream_usage = None

    async def _agent_worker():
        nonlocal full_response, stream_usage
        try:
            async for msg, metadata in agent.astream(
                {"messages": messages},
                stream_mode="messages",
                config={"recursion_limit": AGENT_RECURSION_LIMIT},
            ):
                if not isinstance(msg, AIMessageChunk):
                    continue

                usage = _extract_usage_from_message(msg)
                if usage:
                    stream_usage = usage

                if getattr(msg, "tool_call_chunks", None):
                    continue

                content = ""
                if isinstance(msg.content, str):
                    content = msg.content
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, str):
                            content += block
                        elif isinstance(block, dict) and block.get("type") == "text":
                            content += block.get("text", "")

                if content:
                    full_response += content
                    await output_queue.put({"type": "content", "content": content})
        except Exception as e:
            await output_queue.put({"type": "error", "content": str(e)})
        finally:
            await output_queue.put(None)

    agent_task = asyncio.create_task(_agent_worker())

    try:
        while True:
            event = await output_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
    except GeneratorExit:
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        raise
    finally:
        set_rag_step_queue(None)
        if not agent_task.done():
            agent_task.cancel()
        reset_turn_policy()

    rag_context = get_last_rag_context(clear=True)
    rag_trace = rag_context.get("rag_trace") if rag_context else None
    if not isinstance(rag_trace, dict):
        rag_trace = {}
    mcp_calls = get_mcp_trace(clear=True)
    rag_trace["token_usage"] = _estimate_cost(stream_usage)
    rag_trace["skill"] = plan.to_trace()
    rag_trace["mcp_calls"] = mcp_calls
    rag_trace["mcp_summary"] = _build_mcp_summary(mcp_calls)
    rag_trace["mcp_prefetch_sources"] = prefetched_sources
    rag_trace["mcp_used"] = bool(mcp_calls)

    tool_used = bool(rag_trace.get("tool_used")) if isinstance(rag_trace, dict) else False
    tool_name = rag_trace.get("tool_name") if isinstance(rag_trace, dict) else None

    logger.info(
        "stream_chat_trace user_id=%s session_id=%s tool_used=%s tool_name=%s",
        user_id,
        session_id,
        tool_used,
        tool_name or "none",
    )

    if rag_trace:
        yield f"data: {json.dumps({'type': 'trace', 'rag_trace': rag_trace})}\n\n"

    yield "data: [DONE]\n\n"

    messages.append(AIMessage(content=full_response))
    extra_message_data = [None] * (len(messages) - 1) + [{"rag_trace": rag_trace}]
    storage.save(user_id, session_id, messages, extra_message_data=extra_message_data)
