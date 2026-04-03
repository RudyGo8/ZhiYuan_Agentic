"""
RAG Agent 核心模块
================================================================================
整体流程:
    用户提问 → [1]加载历史对话 → [2]Agent决策 → [3]调用search_knowledge_base工具 
         → [4]RAG检索 → [5]LLM生成答案 → [6]保存对话 → 返回响应
    
核心组件:
    - ConversationStorage: 对话存储 (MySQL + Redis)
    - LangChain Agent: 智能决策 + 工具调用
    - search_knowledge_base: RAG检索工具
================================================================================
"""
from dotenv import load_dotenv
import os
import json
import asyncio
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from app.tools import get_current_weather, search_knowledge_base, get_last_rag_context, reset_tool_call_guards, set_rag_step_queue
from app.config import logger
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")


class ConversationStorage:
    """
    ================================================================================
    [组件1] 对话存储 - ConversationStorage
    ================================================================================
    功能: 管理用户对话历史的持久化和缓存
    
    存储架构:
        MySQL (持久化):
            - db_user: 用户信息
            - db_chat_session: 会话信息 (user_id, session_id, metadata_json)
            - db_chat_message: 消息记录 (session_ref_id, message_type, content, rag_trace)
        
        Redis (缓存加速):
            - chat_messages:{user_id}:{session_id}: 消息缓存
            - chat_sessions:{user_id}: 会话列表缓存
    
    核心方法:
        - save(): 保存对话 (写入MySQL + Redis缓存)
        - load(): 加载对话 (优先Redis缓存，未命中则查MySQL)
        - list_sessions(): 获取用户所有会话
        - delete_session(): 删除会话
    ================================================================================
    """

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
        # Persist one session's full transcript and optional rag trace.
        """保存对话"""
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
        finally:
            db.close()

    def load(self, user_id: str, session_id: str) -> list:
        # Cache-first read path: Redis -> MySQL fallback.
        """加载对话"""
        from app.cache import cache
        
        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return self._to_langchain_messages(cached)

        records = self.get_session_messages(user_id, session_id)
        return self._to_langchain_messages(records)

    def list_sessions(self, user_id: str) -> list:
        # Lightweight helper that only returns session_id list.
        """列出用户的所有会话"""
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
        # Delete DB rows and clear related cache entries.
        """删除指定用户的会话，返回是否删除成功"""
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


def create_agent_instance():
    # Shared singleton factory: model config + tool wiring lives here.

    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )

    agent = create_agent(
        model=model,
        tools=[get_current_weather, search_knowledge_base],
        system_prompt=(
            "You are a helpful AI assistant named 知源 Assistant.You were developed by Rudy."
            "IMPORTANT: You must ALWAYS use tools to answer questions. "
            "For ANY question that might need factual information, documents, or knowledge base content, "
            "you MUST call search_knowledge_base tool first. "
            "Only answer directly if the question is a simple greeting or casual conversation. "
            "After receiving search_knowledge_base result, use that information to answer. "
            "If no relevant documents found, say you don't have that information. "
            "For weather questions, use get_current_weather tool."
        ),
    )
    return agent, model


agent, model = create_agent_instance()

storage = ConversationStorage()


def summarize_old_messages(model, messages: list) -> str:
    # Used as a guardrail against unbounded context growth.
    """将旧消息总结为摘要"""
    old_conversation = "\n".join([
        f"{'用户' if msg.type == 'human' else 'AI'}: {msg.content}"
        for msg in messages
    ])

    summary_prompt = f"""请总结以下对话的关键信息：

{old_conversation}
总结（包含用户信息、重要事实、待办事项）："""

    summary = model.invoke(summary_prompt).content
    return summary


def chat_with_agent(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
    # Sync path for non-streaming endpoint.

    # ============================================================================
    # Step 1: 加载历史对话
    # 优先从 Redis 缓存读取，未命中则从 MySQL 查询
    # ============================================================================
    messages = storage.load(user_id, session_id)

    # ============================================================================
    # Step 2: 重置上下文 (清除上次的 RAG 结果和工具调用计数)
    # ============================================================================
    get_last_rag_context(clear=True)
    reset_tool_call_guards()
    
    # ============================================================================
    # Step 2-1: 长对话压缩 (消息数 > 50)
    # 使用 LLM 总结旧对话，保留最近 40 条 + 摘要
    # ============================================================================
    if len(messages) > 50:
        summary = summarize_old_messages(model, messages[:40])

        messages = [
            SystemMessage(content=f"之前的对话摘要：\n{summary}")
        ] + messages[40:]

    # ============================================================================
    # Step 3: 添加用户消息到对话历史
    # ============================================================================
    messages.append(HumanMessage(content=user_text))
    
    # ============================================================================
    # Step 4: Agent 执行 (核心步骤!)
    # Agent 会分析问题并判断是否需要调用工具
    # 如果需要知识库 → 调用 search_knowledge_base → 触发 RAG Pipeline
    # ============================================================================
    result = agent.invoke(
        {"messages": messages},
        config={"recursion_limit": 8},
    )

    # ============================================================================
    # Step 5: 提取 AI 响应内容
    # ============================================================================
    response_content = ""
    if isinstance(result, dict):
        if "output" in result:
            response_content = result["output"]
        elif "messages" in result and result["messages"]:
            msg = result["messages"][-1]
            response_content = getattr(msg, "content", str(msg))
        else:
            response_content = str(result)
    elif hasattr(result, "content"):
        response_content = result.content
    else:
        response_content = str(result)
    
    # 添加 AI 响应到消息列表
    messages.append(AIMessage(content=response_content))

    # ============================================================================
    # Step 6: 获取 RAG 执行信息 (rag_trace)
    # ============================================================================
    rag_context = get_last_rag_context(clear=True)
    rag_trace = rag_context.get("rag_trace") if rag_context else None

    # ============================================================================
    # Step 7: 保存对话到数据库 (MySQL + Redis 缓存)
    # ============================================================================
    extra_message_data = [None] * (len(messages) - 1) + [{"rag_trace": rag_trace}]
    storage.save(user_id, session_id, messages, extra_message_data=extra_message_data)

    # ============================================================================
    # Step 8: 返回结果
    # ============================================================================
    return {
        "response": response_content,
        "rag_trace": rag_trace,
    }


async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
    """使用 Agent 处理用户消息并流式返回响应。"""
    messages = storage.load(user_id, session_id)

    get_last_rag_context(clear=True)
    reset_tool_call_guards()

    output_queue = asyncio.Queue()

    class _RagStepProxy:
        def put_nowait(self, step):
            output_queue.put_nowait({"type": "rag_step", "step": step})

    set_rag_step_queue(_RagStepProxy())

    if len(messages) > 50:
        summary = summarize_old_messages(model, messages[:40])
        messages = [
            SystemMessage(content=f"之前的对话摘要：\n{summary}")
        ] + messages[40:]

    messages.append(HumanMessage(content=user_text))

    full_response = ""

    async def _agent_worker():
        """生产者协程，消费 agent.astream() 的增量输出，写入 output_queue 供 SSE 消费端发送"""
        nonlocal full_response
        try:
            async for msg, metadata in agent.astream(
                {"messages": messages},
                stream_mode="messages",
                config={"recursion_limit": 8},
            ):
                if not isinstance(msg, AIMessageChunk):
                    continue
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

    rag_context = get_last_rag_context(clear=True)
    rag_trace = rag_context.get("rag_trace") if rag_context else None
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
