'''
@create_time: 2026/4/28
@Author: GeChao
@File: plan_executor.py
'''

from pathlib import Path
from typing import Any

from app.tools.tool_executor import tool_executor


def load_skill_content(skill_name: str) -> str:
    """
    读取 Skill 文档。

    兼容：
    - mcp_integration
    - mcp-integration
    """

    app_root = Path(__file__).resolve().parents[1]

    candidate_names = [
        skill_name,
        skill_name.replace("_", "-"),
    ]

    for name in candidate_names:
        skill_path = app_root / "skills" / name / "SKILL.md"

        if skill_path.exists() and skill_path.is_file():
            return skill_path.read_text(encoding="utf-8")

    raise FileNotFoundError(
        f"未找到 Skill 文档: {skill_name}"
    )


def get_step_input(step: Any) -> dict:
    """
    兼容 Pydantic 对象和 dict。
    """

    if step is None:
        return {}

    if isinstance(step, dict):
        return step.get("input", {}) or {}

    return getattr(step, "input", {}) or {}


async def execute_mcp_integration_plan(execution_plan, user_text: str) -> list[dict]:
    """
    执行 mcp_integration 专用计划。
    """

    trace = []

    # 当前文件位置：backend/app/agent/plan_executor.py
    # parents[2] = backend
    backend_root = Path(__file__).resolve().parents[2]

    context = {
        "user_text": user_text,
        "project_root": str(backend_root),
        "skill_name": "",
        "skill_content": "",
    }

    for step in execution_plan.steps:
        step_type = step.type
        step_id = step.id
        reason = getattr(step, "reason", "")

        if step_type == "load_context":
            trace.append({
                "step_id": step_id,
                "type": step_type,
                "reason": reason,
                "message": "历史上下文已加载",
            })

        elif step_type == "skill_load":
            step_input = get_step_input(step)
            skill_name = step_input.get("skill_name", "mcp_integration")

            skill_content = load_skill_content(skill_name)

            context["skill_name"] = skill_name
            context["skill_content"] = skill_content

            trace.append({
                "step_id": step_id,
                "type": step_type,
                "reason": reason,
                "skill_name": skill_name,
                "message": "Skill 文档加载完成",
            })

        elif step_type in {"tool_call", "call_tool"}:
            tool_name = getattr(step, "tool", None)

            if not tool_name:
                trace.append({
                    "step_id": step_id,
                    "type": step_type,
                    "reason": reason,
                    "success": False,
                    "error": "tool_call step 缺少 tool 字段",
                })
                break

            step_input = get_step_input(step)

            tool_input = {
                **context,
                **step_input,
            }

            result = await tool_executor.execute(
                tool_name=tool_name,
                context=tool_input,
                step=step,
            )

            trace.append({
                "step_id": step_id,
                "type": step_type,
                "tool": tool_name,
                "reason": reason,
                "result": result.to_dict(),
            })

            if not result.success:
                break

        elif step_type == "final_answer":
            trace.append({
                "step_id": step_id,
                "type": step_type,
                "reason": reason,
                "message": "MCP 接入检查流程执行完成",
            })

        else:
            trace.append({
                "step_id": step_id,
                "type": step_type,
                "reason": reason,
                "message": f"暂不支持的 step type: {step_type}",
            })

    return trace
