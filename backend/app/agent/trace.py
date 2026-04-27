import os

from dotenv import load_dotenv

from app.mcp.trace import get_mcp_trace
from app.tools.runtime import get_last_rag_context

load_dotenv()

MODEL = os.getenv("MODEL")


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


def _to_dict(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def extract_usage_from_message(msg) -> dict | None:
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


def collect_rag_trace(plan, usage: dict | None, prefetched_sources: list[str], intent=None, execution_plan=None) -> dict:
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
    rag_trace["intent"] = _to_dict(intent)
    rag_trace["execution_plan"] = _to_dict(execution_plan)
    return rag_trace
