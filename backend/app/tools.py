from contextvars import ContextVar
from typing import Any, Optional
import os
import requests
from dotenv import load_dotenv

try:
    from langchain_core.tools import tool
except ImportError:
    from langchain_core.tools import tool

load_dotenv()

WEATHER_API = os.getenv("WEATHER_API")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEOCODE_API = os.getenv("GEOCODE_API")

_LAST_RAG_CONTEXT: ContextVar[Optional[dict]] = ContextVar("_LAST_RAG_CONTEXT", default=None)
_KNOWLEDGE_TOOL_CALLS_THIS_TURN: ContextVar[int] = ContextVar("_KNOWLEDGE_TOOL_CALLS_THIS_TURN", default=0)
_RAG_STEP_QUEUE: ContextVar[Optional[Any]] = ContextVar("_RAG_STEP_QUEUE", default=None)
_RAG_STEP_LOOP: ContextVar[Optional[Any]] = ContextVar("_RAG_STEP_LOOP", default=None)


def _set_last_rag_context(context: dict):
    _LAST_RAG_CONTEXT.set(context)


def get_last_rag_context(clear: bool = True) -> Optional[dict]:
    context = _LAST_RAG_CONTEXT.get()
    if clear:
        _LAST_RAG_CONTEXT.set(None)
    return context


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


def _resolve_adcode(location: str) -> Optional[str]:
    """获取adcode"""
    if not location or not WEATHER_API_KEY:
        return None

    try:
        resp = requests.get(
            GEOCODE_API,
            params={"key": WEATHER_API_KEY, "address": location},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            return None
        geocodes = data.get("geocodes", [])
        if not geocodes:
            return None
        return geocodes[0].get("adcode")
    except Exception:
        return None


def _request_weather(city: str, extensions: str) -> dict:
    """请求天气"""
    resp = requests.get(
        WEATHER_API,
        params={
            "key": WEATHER_API_KEY,
            "city": city,
            "extensions": extensions,
            "output": "json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_current_weather(location: str, extensions: Optional[str] = "base") -> str:
    """工具：查天气"""
    if not location:
        return "location参数不能为空"
    if extensions not in ("base", "all"):
        return "extensions参数错误，请输入base或all"

    if not WEATHER_API or not WEATHER_API_KEY:
        return "天气服务未配置（缺少 WEATHER_API 或 WEATHER_API_KEY）"

    adcode = _resolve_adcode(location)
    candidates = [adcode, location] if adcode else [location]

    try:
        data = None
        last_info = None
        for city in candidates:
            if not city:
                continue
            current = _request_weather(city=city, extensions=extensions)
            if current.get("status") != "1":
                last_info = current.get("info", "未知错误")
                continue
            if extensions == "base":
                if current.get("lives"):
                    data = current
                    break
                continue
            if current.get("forecasts"):
                data = current
                break

        if data is None:
            if last_info:
                return f"查询失败：{last_info}"
            return f"未查询到 {location} 的天气数据"

        if extensions == "base":
            lives = data.get("lives", [])
            if not lives:
                return f"未查询到 {location} 的天气数据"
            w = lives[0]
            return (
                f"【{w.get('city', location)} 实时天气】\n"
                f"天气状况：{w.get('weather', '未知')}\n"
                f"温度：{w.get('temperature', '未知')}℃\n"
                f"湿度：{w.get('humidity', '未知')}%\n"
                f"风向：{w.get('winddirection', '未知')}\n"
                f"风力：{w.get('windpower', '未知')}级\n"
                f"更新时间：{w.get('reporttime', '未知')}"
            )

        forecasts = data.get("forecasts", [])
        if not forecasts:
            return f"未查询到 {location} 的天气预报数据"
        f0 = forecasts[0]
        out = [
            f"【{f0.get('city', location)} 天气预报】",
            f"更新时间：{f0.get('reporttime', '未知')}",
            "",
        ]
        today = (f0.get("casts") or [])[0] if f0.get("casts") else {}
        out += [
            "今日天气：",
            f"  白天：{today.get('dayweather', '未知')}",
            f"  夜间：{today.get('nightweather', '未知')}",
            f"  气温：{today.get('nighttemp', '未知')}~{today.get('daytemp', '未知')}℃",
        ]
        return "\n".join(out)
    except requests.exceptions.Timeout:
        return "错误：请求天气服务超时"
    except requests.exceptions.RequestException as e:
        return f"错误：天气服务请求失败 - {e}"
    except Exception as e:
        return f"错误：解析天气数据失败 - {e}"


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """工具：检索知识库"""
    calls_this_turn = _KNOWLEDGE_TOOL_CALLS_THIS_TURN.get()
    if calls_this_turn >= 1:
        return (
            "TOOL_CALL_LIMIT_REACHED: search_knowledge_base has already been called once in this turn. "
            "Use the existing retrieval result and provide the final answer directly."
        )
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN.set(calls_this_turn + 1)

    from app.rag_pipeline import run_rag_graph

    rag_result = run_rag_graph(query)

    docs = rag_result.get("docs", []) if isinstance(rag_result, dict) else []
    rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
    if rag_trace:
        _set_last_rag_context({"rag_trace": rag_trace})

    if not docs:
        return "No relevant documents found in the knowledge base."

    formatted = []
    for i, result in enumerate(docs, 1):
        source = result.get("filename", "Unknown")
        page = result.get("page_number", "N/A")
        text = result.get("text", "")
        formatted.append(f"[{i}] {source} (Page {page}):\n{text}")

    return "Retrieved Chunks:\n" + "\n\n---\n\n".join(formatted)
