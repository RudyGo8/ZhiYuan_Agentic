from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.skills.base import SkillPlan


@dataclass
class SkillDefinition:
    name: str
    display_name: str
    description: str
    keywords: list[str]
    use_mcp: bool
    mcp_sources: list[str]
    priority: int
    output_template: str = ""
    skill_doc: str = ""


def _normalize_source_name(source: str) -> str:
    value = (source or "").strip().lower()
    if value == "db":
        return "mysql"
    return value


def _normalize_sources(sources: list[str] | None) -> list[str]:
    result: list[str] = []
    for source in sources or []:
        normalized = _normalize_source_name(str(source))
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _skillpacks_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "skillpacks"


def build_default_plan(use_mcp: bool = False, mcp_sources: list[str] | None = None) -> SkillPlan:
    normalized_sources = _normalize_sources(mcp_sources)
    return SkillPlan(
        name="default_rag",
        display_name="默认问答",
        use_mcp=use_mcp,
        mcp_sources=normalized_sources if use_mcp else [],
        output_template="",
    )


def build_db_schema_plan(use_mcp: bool = True) -> SkillPlan:
    return SkillPlan(
        name="db_schema",
        display_name="数据库字段分析",
        use_mcp=use_mcp,
        mcp_sources=["mysql"] if use_mcp else [],
        output_template=(
            "请按以下结构输出：\n"
            "1) 涉及表\n"
            "2) 涉及字段\n"
            "3) 字段作用说明\n"
            "4) 表之间关系\n"
            "5) 结论\n"
        ),
    )


def load_skill_definitions() -> list[SkillDefinition]:
    root = _skillpacks_dir()
    if not root.exists():
        return []

    definitions: list[SkillDefinition] = []
    for item in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir():
            continue

        meta_path = item / "meta.json"
        if not meta_path.exists():
            continue

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        name = str(meta.get("name") or item.name).strip()
        if not name:
            continue

        display_name = str(meta.get("display_name") or name).strip()
        description = str(meta.get("description") or "").strip()
        keywords = [
            str(keyword).strip().lower()
            for keyword in (meta.get("keywords") or [])
            if str(keyword).strip()
        ]
        use_mcp = bool(meta.get("use_mcp"))
        mcp_sources = _normalize_sources(meta.get("mcp_sources") or [])
        priority = int(meta.get("priority") or 0)

        template_path = item / "templates" / "output.md"
        output_template = template_path.read_text(encoding="utf-8").strip() if template_path.exists() else ""

        skill_md_path = item / "SKILL.md"
        skill_doc = skill_md_path.read_text(encoding="utf-8").strip() if skill_md_path.exists() else ""

        definitions.append(
            SkillDefinition(
                name=name,
                display_name=display_name,
                description=description,
                keywords=keywords,
                use_mcp=use_mcp,
                mcp_sources=mcp_sources,
                priority=priority,
                output_template=output_template,
                skill_doc=skill_doc,
            )
        )

    definitions.sort(key=lambda d: (d.priority, d.name), reverse=True)
    return definitions


def build_plan_from_definition(definition: SkillDefinition) -> SkillPlan:
    return SkillPlan(
        name=definition.name,
        display_name=definition.display_name,
        use_mcp=definition.use_mcp,
        mcp_sources=_normalize_sources(definition.mcp_sources) if definition.use_mcp else [],
        output_template=definition.output_template,
    )
