import re

from app.skills.base import SkillPlan
from app.skills.registry import build_db_schema_plan, build_default_plan

DB_KEYWORDS = (
    "数据库", "表", "字段", "列", "索引", "外键", "ddl", "schema", "sql", "mysql", "postgres",
    "database", "table", "field", "column", "columns", "index",
)
GIT_KEYWORDS = (
    "提交", "变更", "仓库", "分支", "pr", "commit", "github", "gitlab", "repo",
)
LOG_KEYWORDS = (
    "日志", "报错", "错误", "异常", "堆栈", "traceback", "error", "log",
)
REALTIME_KEYWORDS = (
    "最新", "当前", "最近", "今天", "实时", "latest", "current", "recent", "today",
)


def _contains_keyword(text: str, keyword: str) -> bool:
    key = (keyword or "").strip().lower()
    if not key:
        return False
    if key.isascii() and key.replace("_", "").isalnum():
        pattern = rf"(?<![a-z0-9_]){re.escape(key)}(?![a-z0-9_])"
        return re.search(pattern, text) is not None
    return key in text


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _pick_mcp_sources(text: str) -> list[str]:
    sources: list[str] = []
    if _contains_any(text, DB_KEYWORDS):
        sources.append("db")
    if _contains_any(text, GIT_KEYWORDS):
        sources.append("git")
    if _contains_any(text, LOG_KEYWORDS):
        sources.append("log")

    if not sources and _contains_any(text, REALTIME_KEYWORDS):
        sources.append("git")
    return sources


def route_skill(query: str) -> SkillPlan:
    text = (query or "").strip().lower()
    if not text:
        return build_default_plan()

    if _contains_any(text, DB_KEYWORDS):
        return build_db_schema_plan(use_mcp=True)

    mcp_sources = _pick_mcp_sources(text)
    return build_default_plan(use_mcp=bool(mcp_sources), mcp_sources=mcp_sources)


def build_skill_prompt(user_query: str, plan: SkillPlan) -> str:
    if plan.name == "default_rag":
        return user_query
    mcp_tip = (
        f"请优先调用以下外部来源获取实时：{', '.join(plan.mcp_sources)}。若调用失败，请在结论中明确说明。"
        if plan.use_mcp and plan.mcp_sources
        else "优先使用知识库回答，若证据不足请明确说明限制。"
    )
    return (
        f"用户原始问题：{user_query}\n\n"
        f"请以“{plan.display_name}”模式回答。\n"
        f"{mcp_tip}\n"
        f"{plan.output_template}\n"
    )
