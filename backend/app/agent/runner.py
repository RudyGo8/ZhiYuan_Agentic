import asyncio
import json

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.agent.context import initialize_turn, prepare_messages
from app.agent.factory import get_agent, get_recursion_limit
from app.agent.prompt import build_turn_prompt
from app.agent.trace import collect_rag_trace, extract_usage_from_message
from app.config import logger
from app.mcp.policy import reset_turn_policy
from app.services.conversation_service import conversation_service as storage
from app.services.intent_service import intent_service
from app.services.planner_service import planner_service
from app.skills.router import route_skill
from app.tools import set_rag_step_queue


async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
    messages = storage.load(user_id, session_id)
    messages = prepare_messages(messages)
    intent = intent_service.classify(user_text)
    execution_plan = planner_service.create_plan(user_text, intent)

    skill_plan = route_skill(user_text)

    if intent.required_knowledge_base:
        skill_plan.require_rag = True

    if intent.required_realtime and "mcp" in intent.tool_candidates:
        skill_plan.use_mcp = True
        skill_plan.mcp_sources = skill_plan.mcp_sources or ["git"]

    initialize_turn(skill_plan)

    output_queue = asyncio.Queue()

    class _RagStepProxy:
        def put_nowait(self, step):
            output_queue.put_nowait({"type": "rag_step", "step": step})

    set_rag_step_queue(_RagStepProxy())

    if getattr(skill_plan, "use_mcp", False):
        yield f"data: {json.dumps({'type': 'rag_step', 'step': {'icon': '⏳', 'label': '处理中', 'detail': '正在获取外部实时证据...'}})}\n\n"

    skill_prompt, prefetched_sources = build_turn_prompt(user_text, skill_plan, user_id)
    messages.append(HumanMessage(content=skill_prompt))

    full_response = ""
    stream_usage = None

    async def _agent_worker():
        nonlocal full_response, stream_usage
        try:
            async for msg, _metadata in get_agent().astream(
                {"messages": messages},
                stream_mode="messages",
                config={"recursion_limit": get_recursion_limit()},
            ):
                if not isinstance(msg, AIMessageChunk):
                    continue

                usage = extract_usage_from_message(msg)
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

    rag_trace = collect_rag_trace(skill_plan, stream_usage, prefetched_sources, intent, execution_plan)

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
