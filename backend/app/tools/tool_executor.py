'''
@create_time: 2026/4/28 上午1:26
@Author: GeChao
@File: tool_executor.py
'''
"""
@create_time: 2026/4/28
@Author: GeChao
@File: tool_executor.py

工具执行器：
根据 planner 生成的 tool 名称，从 registry 中找到对应工具并执行。
"""

import inspect
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

from app.config import logger
from app.tools.registry import get_tool


@dataclass
class ToolExecutionResult:
    """
    工具执行结果统一结构
    """
    tool: str
    success: bool
    input: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: str | None = None
    elapsed_ms: int = 0
    traceback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ToolExecutor:
    async def execute(
        self,
        tool_name: str,
        context: dict[str, Any] | None = None,
        step: Any = None,
    ) -> ToolExecutionResult:
        start_time = time.time()
        context = context or {}

        try:
            tool = get_tool(tool_name)

            tool_context = self._build_tool_context(context, step)

            output = await self._call_tool(
                tool=tool,
                context=tool_context,
                step=step,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            return ToolExecutionResult(
                tool=tool_name,
                success=True,
                input=tool_context,
                output=output,
                elapsed_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            tb = traceback.format_exc()

            logger.error(
                f"工具执行失败: {tool_name}, error={str(e)}",
                exc_info=True,
            )

            return ToolExecutionResult(
                tool=tool_name,
                success=False,
                input=context,
                error=str(e),
                elapsed_ms=elapsed_ms,
                traceback=tb,
            )

    def _build_tool_context(
            self,
            context: dict[str, Any],
            step: Any = None,
    ) -> dict[str, Any]:
        """
        合并全局 context 和 step.input。

        例如：
        context = {
            "project_root": ".../backend"
        }

        step.input = {
            "validate_command": "python -m compileall app"
        }

        合并后：
        {
            "project_root": ".../backend",
            "validate_command": "python -m compileall app"
        }
        """

        tool_context = dict(context)

        step_input = {}

        if step is not None:
            if isinstance(step, dict):
                step_input = step.get("input", {}) or {}
            else:
                step_input = getattr(step, "input", {}) or {}

        if isinstance(step_input, dict):
            tool_context.update(step_input)

        return tool_context

    async def _call_tool(
            self,
            tool: Any,
            context: dict[str, Any],
            step: Any = None,
    ) -> Any:
        """
        兼容你的工具写法：
        async def run(self, context: dict, step=None)
        """

        if hasattr(tool, "run") and callable(tool.run):
            result = tool.run(context, step=step)
            if inspect.isawaitable(result):
                return await result
            return result

        if inspect.iscoroutinefunction(tool):
            return await tool(context)

        if callable(tool):
            result = tool(context)
            if inspect.isawaitable(result):
                return await result
            return result

        raise TypeError(f"不支持的工具类型: {type(tool)}")

tool_executor = ToolExecutor()