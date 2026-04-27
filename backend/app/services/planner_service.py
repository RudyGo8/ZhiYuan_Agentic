'''
@create_time: 2026/4/26 下午9:13
@Author: GeChao
@File: planner_service.py
'''
from app.schemas.agent_intent import AgentIntent
from app.schemas.agent_plan import AgentPlan, PlanStep


class PlannerService:
    @staticmethod
    def _step(
        step_id: str,
        step_type: str,
        tool: str | None = None,
        input: dict | None = None,
        reason: str = "",
    ) -> PlanStep:
        return PlanStep(
            id=step_id,
            type=step_type,
            tool=tool,
            input=input or {},
            reason=reason,
        )

    def create_plan(self, user_text: str, intent: AgentIntent) -> AgentPlan:
        if intent.intent == "casual_chat":
            return AgentPlan(
                task_type=" casual_chat",
                steps=[
                    self._step("load_context", "load_context", reason="加载历史会话"),
                    self._step("final_answer", "final_answer", reason="无需工具，直接回答"),
                ],
            )

        if intent.intent == "mcp_integration":
            return AgentPlan(
                task_type="mcp_integration",
                steps=[
                    self._step("load_context", "load_context", reason="加载历史会话"),
                    self._step("load_mcp_integration_skill", "skill_load", input= {"skill_name": "mcp_integration"}, reason="读取 mcp_integration Skill 文档，获取 MCP 接入流程和安全规则"),
                    self._step("inspect_project_mcp", "tool_call", tool="project_file_reader", reason="读取项目中现有 MCP 配置、client_manager、config 和 pyproject 文件"),
                    self._step("generate_mcp_config_suggestion","tool_call", tool="project_code_editor", reason="根据 Skill 流程生成 MCP Server 配置和注册建议"),
                    self._step("validate_config","call_tool", tool="project_shell", input={"validate_command": "python -m compileall app"}, reason="运行基础校验，确认配置格式正确"),
                    self._step("final_answer","final_answer", reason="输出 MCP 接入建议、配置说明和启动方式"),
                ]
            )

        if intent.intent == "rag_qa":
            return self._tool_plan("rag_qa", "search_knowledge_base", "检索知识库")
        if intent.intent == "realtime_query":
            return self._tool_plan("realtime_query", "mcp", "获取实时信息")
        if intent.intent == "database_query":
            return self._tool_plan("database_query", "database", "查询数据库")
        if intent.intent == "weather_query":
            return self._tool_plan("weather_query", "get_current_weather", "查询天气")



        return AgentPlan(
            task_type="unknown",
            steps=[
                self._step("load_context", "load_context", reason="加载历史会话"),
                self._step("final_answer", "final_answer", reason="没有明确工具需求，先直接回答"),
            ]

        )

    def _tool_plan(self, task_type: str, tool: str, reason: str) -> AgentPlan:
        return AgentPlan(
            task_type=task_type,
            steps=[
                self._step("load_context", "load_context", reason="加载历史会话"),
                self._step(f"call_{tool}", "call_tool", tool=tool, reason=reason),
                self._step("evaluate_result", "evaluate_result", reason="判断工具结果是否足够"),
                self._step("final_answer", "final_answer", reason="生成最终回答"),

            ]
        )


planner_service = PlannerService()
