import asyncio
import json
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from app.agent.context import prepare_messages
from app.agent.factory import get_agent, get_recursion_limit, create_agent_instance
from app.agent.prompt import build_turn_prompt
from app.agent.trace import collect_rag_trace, extract_usage_from_message
from app.config import logger
from app.mcp import mcp_client_manager
from app.services.conversation_service import conversation_service as storage
from app.tools.runtime import get_last_rag_context, reset_tool_call_guards, set_rag_step_queue
from app.tools.registry import TOOL_REGISTRY


async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session"):
    get_last_rag_context(clear=True)
    reset_tool_call_guards()
    messages = storage.load(user_id, session_id)
    messages = prepare_messages(messages)

    local_tools = [spec.tool for spec in TOOL_REGISTRY.values()]
    mcp_tools = await mcp_client_manager.get_agent_tools()
    candidate_tools = local_tools + mcp_tools
    agent, _ = create_agent_instance(tools=candidate_tools)
    output_queue = asyncio.Queue()

    class _RagStepProxy:
        def put_nowait(self, step):
            output_queue.put_nowait({"type": "rag_step", "step": step})

    set_rag_step_queue(_RagStepProxy())

    build_prompt = build_turn_prompt(user_text, user_id)
    agent_messages = [*messages, HumanMessage(content=build_prompt)]

    full_response = ""
    stream_usage = None

    async def _agent_worker():
        nonlocal full_response, stream_usage
        try:
            async for msg, _metadata in agent.astream(
                    {"messages": agent_messages},
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

    rag_trace = collect_rag_trace(stream_usage)

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

    persisted_messages = [*messages, HumanMessage(content=user_text), AIMessage(content=full_response)]
    extra_message_data = [None] * (len(persisted_messages) - 1) + [{"rag_trace": rag_trace}]
    storage.save(user_id, session_id, persisted_messages, extra_message_data=extra_message_data)
