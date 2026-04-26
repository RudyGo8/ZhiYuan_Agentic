import re

from app.skills.base import SkillPlan
from app.skills.registry import build_default_plan, build_plan_from_definition, load_skill_definitions

REALTIME_KEYWORDS = (
    "最新", "当前", "最近", "今天", "实时",
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


def _extract_hint_terms(description: str) -> list[str]:
    text = (description or "").strip().lower()
    if not text:
        return []
    raw_terms = re.split(r"[\s,，。；;:：\(\)（）/\|]+", text)
    terms: list[str] = []
    for term in raw_terms:
        cleaned = term.strip()
        if len(cleaned) < 2:
            continue
        if cleaned not in terms:
            terms.append(cleaned)
    return terms[:40]


def _score_definition(text: str, definition) -> int:
    score = 0
    for keyword in definition.keywords:
        if _contains_keyword(text, keyword):
            score += 3

    if _contains_keyword(text, definition.name):
        score += 2

    for term in _extract_hint_terms(definition.description):
        if _contains_keyword(text, term):
            score += 1
    return score


def route_skill(query: str) -> SkillPlan:
    text = (query or "").strip().lower()
    if not text:
        return build_default_plan()

    skill_definitions = load_skill_definitions()
    best_match = None
    best_rank = (-1, -1)

    for definition in skill_definitions:
        score = _score_definition(text, definition)
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
        f"请优先调用以下外部来源获取实时信息：{', '.join(plan.mcp_sources)}。若调用失败，请在结论中明确说明。"
        if plan.use_mcp and plan.mcp_sources
        else "请优先使用知识库回答；若证据不足，请明确说明限制。"
    )
    allowed_tools_tip = (
        f"本轮允许工具：{', '.join(plan.allowed_tools)}。"
        if plan.allowed_tools
        else ""
    )
    skill_instruction = (plan.skill_doc or plan.output_template or "").strip()

    parts = [
        f"用户原始问题：{user_query}",
        f"请以“{plan.display_name}”模式回答。",
        mcp_tip,
    ]
    if allowed_tools_tip:
        parts.append(allowed_tools_tip)
    if skill_instruction:
        parts.append(f"请严格遵循以下 Skill 说明：\n{skill_instruction}")
    return "\n\n".join(parts).strip()
