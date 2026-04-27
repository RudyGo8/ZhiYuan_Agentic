'''
@create_time: 2026/4/28 上午12:24
@Author: GeChao
@File: runtime.py
'''

from contextvars import ContextVar
from typing import Any, Optional

_LAST_RAG_CONTEXT: ContextVar[Optional[dict]] = ContextVar("_LAST_RAG_CONTEXT", default=None)
_KNOWLEDGE_TOOL_CALLS_THIS_TURN: ContextVar[int] = ContextVar("_KNOWLEDGE_TOOL_CALLS_THIS_TURN", default=0)
_RAG_STEP_QUEUE: ContextVar[Optional[Any]] = ContextVar("_RAG_STEP_QUEUE", default=None)
_RAG_STEP_LOOP: ContextVar[Optional[Any]] = ContextVar("_RAG_STEP_LOOP", default=None)


def set_last_rag_context(context: dict):
    _LAST_RAG_CONTEXT.set(context)


def get_last_rag_context(clear: bool = True) -> Optional[dict]:
    context = _LAST_RAG_CONTEXT.get()
    if clear:
        _LAST_RAG_CONTEXT.set(None)
    return context


def increase_knowledge_tool_calls_this_turn():
    current = _KNOWLEDGE_TOOL_CALLS_THIS_TURN.get()
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN.set(current + 1)


def get_knowledge_tool_call_this_turn() -> int:
    return _KNOWLEDGE_TOOL_CALLS_THIS_TURN.get()


def reset_tool_call_guards():
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN.set(0)


def set_rag_step_queue(queue):
    _RAG_STEP_QUEUE.set(queue)
    if queue:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
        _RAG_STEP_LOOP.set(loop)
    else:
        _RAG_STEP_LOOP.set(None)


def emit_rag_step(icon: str, label: str, detail: str = ""):
    queue = _RAG_STEP_QUEUE.get()
    loop = _RAG_STEP_LOOP.get()
    if queue is not None and loop is not None:
        step = {"icon": icon, "label": label, "detail": detail}
        try:
            if not loop.is_closed():
                loop.call_soon_threadsafe(queue.put_nowait, step)
        except Exception:
            pass
