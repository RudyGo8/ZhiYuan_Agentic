from app.skills.base import SkillPlan


def build_default_plan(use_mcp: bool = False, mcp_sources: list[str] | None = None) -> SkillPlan:
    return SkillPlan(
        name="default_rag",
        display_name="默认问答",
        use_mcp=use_mcp,
        mcp_sources=(mcp_sources or []) if use_mcp else [],
        output_template="",
    )


def build_db_schema_plan(use_mcp: bool = True) -> SkillPlan:
    return SkillPlan(
        name="db_schema",
        display_name="数据库字段分析",
        use_mcp=use_mcp,
        mcp_sources=["db"] if use_mcp else [],
        output_template=(
            "请按以下结构输出：\n"
            "1) 涉及表\n"
            "2) 涉及字段\n"



        ),
    )
