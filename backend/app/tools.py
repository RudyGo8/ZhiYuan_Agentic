"""
工具模块 - Tools
================================================================================
本模块定义 LangChain Agent 可调用的工具函数

工具列表:
    1. search_knowledge_base: RAG检索工具 (核心!)
    2. get_current_weather: 天气查询工具

全局状态变量:
    - _LAST_RAG_CONTEXT: 存储最近一次 RAG 执行结果
    - _KNOWLEDGE_TOOL_CALLS_THIS_TURN: 记录本轮知识库工具调用次数 (防重复)
    - _RAG_STEP_QUEUE: 用于流式输出的步骤队列
================================================================================
"""
from typing import Optional
import os
import requests
from dotenv import load_dotenv

try:
    from langchain_core.tools import tool
except ImportError:
    from langchain_core.tools import tool

load_dotenv()

AMAP_WEATHER_API = os.getenv("AMAP_WEATHER_API")
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

_LAST_RAG_CONTEXT = None  # 存储最近一次 RAG 执行结果，供 agent.py 读取
_KNOWLEDGE_TOOL_CALLS_THIS_TURN = 0  # 防重复调用计数器
_RAG_STEP_QUEUE = None  # 流式输出队列
_RAG_STEP_LOOP = None  # 异步事件循环


def _set_last_rag_context(context: dict):
    # Store latest retrieval metadata for downstream response assembly.
    """设置 RAG 上下文 (供 agent.py 读取 rag_trace)"""
    global _LAST_RAG_CONTEXT
    _LAST_RAG_CONTEXT = context


def get_last_rag_context(clear: bool = True) -> Optional[dict]:
    # Read latest retrieval metadata and optionally clear it.
    """获取并清除 RAG 上下文"""
    global _LAST_RAG_CONTEXT
    context = _LAST_RAG_CONTEXT
    if clear:
        _LAST_RAG_CONTEXT = None
    return context


def reset_tool_call_guards():
    # Reset tool-call counter at the beginning of each turn.
    """重置工具调用计数器 (每轮对话开始时调用)"""
    global _KNOWLEDGE_TOOL_CALLS_THIS_TURN
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN = 0


def set_rag_step_queue(queue):
    # Register queue sink used to stream RAG progress steps to the client.
    """设置 RAG 步骤队列 (用于流式输出)"""
    global _RAG_STEP_QUEUE, _RAG_STEP_LOOP
    _RAG_STEP_QUEUE = queue
    if queue:
        import asyncio
        try:
            _RAG_STEP_LOOP = asyncio.get_running_loop()
        except RuntimeError:
            _RAG_STEP_LOOP = asyncio.get_event_loop()
    else:
        _RAG_STEP_LOOP = None


def emit_rag_step(icon: str, label: str, detail: str = ""):
    """进度条信息-流式输出"""
    global _RAG_STEP_QUEUE, _RAG_STEP_LOOP
    if _RAG_STEP_QUEUE is not None and _RAG_STEP_LOOP is not None:
        step = {"icon": icon, "label": label, "detail": detail}
        try:
            if not _RAG_STEP_LOOP.is_closed():
                _RAG_STEP_LOOP.call_soon_threadsafe(_RAG_STEP_QUEUE.put_nowait, step)
        except Exception:
            pass


# ===============================================================================
# [工具1] 天气查询工具
# ===============================================================================
def get_current_weather(location: str, extensions: Optional[str] = "base") -> str:
    # Wrapper around weather API with consistent error handling.
    """
    ================================================================================
    [工具1] get_current_weather - 天气查询工具
    ================================================================================
    说明: 调用高德地图天气API获取实时天气或预报信息
    
    参数:
        - location: 城市名称 (如 "北京")
        - extensions: "base"(实时天气) 或 "all"(天气预报)
    
    返回: 格式化的天气信息字符串
    ================================================================================
    """
    if not location:
        return "location参数不能为空"
    if extensions not in ("base", "all"):
        return "extensions参数错误，请输入base或all"

    if not AMAP_WEATHER_API or not AMAP_API_KEY:
        return "天气服务未配置（缺少 AMAP_WEATHER_API 或 AMAP_API_KEY）"

    params = {
        "key": AMAP_API_KEY,
        "city": location,
        "extensions": extensions,
        "output": "json",
    }

    try:
        resp = requests.get(AMAP_WEATHER_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            return f"查询失败：{data.get('info', '未知错误')}"

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
        out = [f"【{f0.get('city', location)} 天气预报】", f"更新时间：{f0.get('reporttime', '未知')}", ""]
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


# ===============================================================================
# [工具2] RAG 检索工具 (核心!)
# ===============================================================================
@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    # Main retrieval tool exposed to the agent.
    """Search the RAG knowledge base and return formatted retrieved chunks."""

    global _KNOWLEDGE_TOOL_CALLS_THIS_TURN

    if _KNOWLEDGE_TOOL_CALLS_THIS_TURN >= 1:
        return (
            "TOOL_CALL_LIMIT_REACHED: search_knowledge_base has already been called once in this turn. "
            "Use the existing retrieval result and provide the final answer directly."
        )
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN += 1

    # Tool Step 2: 调用 RAG Pipeline (核心!)

    from app.rag_pipeline import run_rag_graph

    rag_result = run_rag_graph(query)

    # ============================================================================
    # Tool Step 3: 提取检索结果和元数据
    # 保存 rag_trace，供 agent.py 的 chat_with_agent() 读取
    # ============================================================================
    docs = rag_result.get("docs", []) if isinstance(rag_result, dict) else []
    rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
    if rag_trace:
        # 保存 rag_trace，供 agent.py 的 chat_with_agent() 读取
        _set_last_rag_context({"rag_trace": rag_trace})

    # ============================================================================
    # Tool Step 4: 格式化返回结果
    # ============================================================================
    if not docs:
        return "No relevant documents found in the knowledge base."

    formatted = []
    for i, result in enumerate(docs, 1):
        source = result.get("filename", "Unknown")
        page = result.get("page_number", "N/A")
        text = result.get("text", "")
        formatted.append(f"[{i}] {source} (Page {page}):\n{text}")

    return "Retrieved Chunks:\n" + "\n\n---\n\n".join(formatted)
