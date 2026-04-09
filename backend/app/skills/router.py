import re

from app.skills.base import SkillPlan
from app.skills.registry import build_default_plan, build_plan_from_definition, load_skill_definitions

REALTIME_KEYWORDS = (
    "\u6700\u65b0", "\u5f53\u524d", "\u6700\u8fd1", "\u4eca\u5929", "\u5b9e\u65f6",
    "latest", "current", "recent", "today",
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


def _score_keywords(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if _contains_keyword(text, keyword))


# 识别技能
def route_skill(query: str) -> SkillPlan:
    text = (query or "").strip().lower()
    if not text:
        return build_default_plan()

    skill_definitions = load_skill_definitions()
    best_match = None
    best_rank = (-1, -1)

    for definition in skill_definitions:
        score = _score_keywords(text, definition.keywords)
        if score <= 0:
            continue
        rank = (score, definition.priority)
        if rank > best_rank:
            best_rank = rank
            best_match = definition

    if best_match is not None:
        return build_plan_from_definition(best_match)

    if _contains_any(text, REALTIME_KEYWORDS):
        return build_default_plan(use_mcp=True, mcp_sources=["git"])

    return build_default_plan()


def build_skill_prompt(user_query: str, plan: SkillPlan) -> str:
    if plan.name == "default_rag":
        return user_query

    mcp_tip = (
        f"请优先调用以下外部来源获取实时信息：{', '.join(plan.mcp_sources)}\u3002"
        "若调用失败，请在结论中明确说明。"
        if plan.use_mcp and plan.mcp_sources
        else "优先使用知识库回答，若证据不足请明确说明限制。"
    )
    return (
        f"用户原始问题：{user_query}\n\n"
        f"请以“{plan.display_name}”模式回答。"
        f"{mcp_tip}\n"
        f"{plan.output_template}\n"
    )
