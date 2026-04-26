from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    compatibility: str = ""
    allowed_tools: list[str] = field(default_factory=list)


def _normalize_source_name(source: str) -> str:
    return (source or "").strip().lower()


def _normalize_tool_name(tool: str) -> str:
    return (tool or "").strip().lower()


def _normalize_sources(sources: list[str] | None) -> list[str]:
    result: list[str] = []
    for source in sources or []:
        normalized = _normalize_source_name(str(source))
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _normalize_tools(tools: list[str] | None) -> list[str]:
    result: list[str] = []
    for item in tools or []:
        normalized = _normalize_tool_name(str(item))
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _skillpacks_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "skillpacks"


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _parse_scalar(value: str) -> Any:
    text = (value or "").strip()
    if not text:
        return ""

    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]

    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", text):
        try:
            return int(text)
        except Exception:
            return text
    if text.startswith("[") and text.endswith("]"):
        inside = text[1:-1].strip()
        if not inside:
            return []
        return [_parse_scalar(item.strip()) for item in inside.split(",") if item.strip()]
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return text


def _parse_simple_yaml(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if line.startswith(" ") or ":" not in line:
            i += 1
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip().lower()
        value = raw_value.strip()
        if value:
            data[key] = _parse_scalar(value)
            i += 1
            continue

        i += 1
        block: list[str] = []
        while i < len(lines):
            sub = lines[i]
            if not sub.strip():
                i += 1
                continue
            if len(sub) - len(sub.lstrip()) == 0:
                break
            block.append(sub)
            i += 1

        if not block:
            data[key] = ""
            continue

        first = block[0].lstrip()
        if first.startswith("- "):
            items: list[Any] = []
            for sub in block:
                sub_stripped = sub.lstrip()
                if sub_stripped.startswith("- "):
                    items.append(_parse_scalar(sub_stripped[2:].strip()))
            data[key] = items
            continue

        nested: dict[str, Any] = {}
        for sub in block:
            sub_stripped = sub.lstrip()
            if ":" not in sub_stripped:
                continue
            nested_key, nested_value = sub_stripped.split(":", 1)
            nested[nested_key.strip().lower()] = _parse_scalar(nested_value.strip())
        data[key] = nested

    return data


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    text = (raw or "").lstrip("\ufeff")
    if not text:
        return {}, ""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    end_index = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break

    if end_index <= 0:
        return {}, text.strip()

    frontmatter = _parse_simple_yaml(lines[1:end_index])
    body = "\n".join(lines[end_index + 1:]).strip()
    return frontmatter, body


def _to_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            result.extend(_to_string_list(item))
        return result
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if "," in text or "\uFF0C" in text:
            parts = re.split("[,\uFF0C]", text)
            return [part.strip() for part in parts if part.strip()]
        return [text]
    return [str(value).strip()] if str(value).strip() else []


def _to_keywords(value: Any) -> list[str]:
    result: list[str] = []
    for keyword in _to_string_list(value):
        normalized = keyword.lower()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _parse_allowed_tools(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    text = text.replace(",", " ")
    return [item.strip() for item in text.split() if item.strip()]


def _resolve_bool(*values: Any, default: bool = False) -> bool:
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in {"true", "1", "yes", "y", "on"}:
                return True
            if low in {"false", "0", "no", "n", "off"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
    return default


def _resolve_int(*values: Any, default: int = 0) -> int:
    for value in values:
        if value is None:
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return int(value.strip())
            except Exception:
                continue
    return default


def build_default_plan(use_mcp: bool = False, mcp_sources: list[str] | None = None) -> SkillPlan:
    normalized_sources = _normalize_sources(mcp_sources)
    return SkillPlan(
        name="default_rag",
        display_name="默认知识库",
        use_mcp=use_mcp,
        mcp_sources=normalized_sources if use_mcp else [],
        output_template="",
        skill_doc="",
        allowed_tools=[],
    )


def load_skill_definitions() -> list[SkillDefinition]:
    root = _skillpacks_dir()
    if not root.exists():
        return []

    definitions: list[SkillDefinition] = []
    for item in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir():
            continue

        meta: dict[str, Any] = {}
        meta_path = item / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}

        frontmatter: dict[str, Any] = {}
        skill_doc = ""
        skill_md_path = item / "SKILL.md"
        if skill_md_path.exists():
            try:
                frontmatter, skill_doc = _split_frontmatter(skill_md_path.read_text(encoding="utf-8"))
            except Exception:
                frontmatter, skill_doc = {}, ""

        metadata = frontmatter.get("metadata")
        metadata_map = {
            str(key).strip().lower(): value
            for key, value in (metadata.items() if isinstance(metadata, dict) else [])
        }

        name = str(_first_non_empty(frontmatter.get("name"), meta.get("name"), item.name) or "").strip()
        if not name:
            continue

        display_name = str(
            _first_non_empty(
                frontmatter.get("display-name"),
                frontmatter.get("display_name"),
                metadata_map.get("display_name"),
                meta.get("display_name"),
                name,
            )
            or name
        ).strip()

        description = str(
            _first_non_empty(
                frontmatter.get("description"),
                meta.get("description"),
                display_name,
            )
            or display_name
        ).strip()

        keywords = _to_keywords(
            _first_non_empty(
                frontmatter.get("keywords"),
                metadata_map.get("keywords"),
                meta.get("keywords"),
            )
        )

        use_mcp = _resolve_bool(
            frontmatter.get("use-mcp"),
            frontmatter.get("use_mcp"),
            metadata_map.get("use_mcp"),
            meta.get("use_mcp"),
            default=False,
        )

        mcp_sources = _normalize_sources(
            _to_string_list(
                _first_non_empty(
                    frontmatter.get("mcp-sources"),
                    frontmatter.get("mcp_sources"),
                    metadata_map.get("mcp_sources"),
                    meta.get("mcp_sources"),
                    [],
                )
            )
        )
        if mcp_sources:
            use_mcp = True

        priority = _resolve_int(
            frontmatter.get("priority"),
            metadata_map.get("priority"),
            meta.get("priority"),
            default=0,
        )

        compatibility = str(
            _first_non_empty(
                frontmatter.get("compatibility"),
                meta.get("compatibility"),
                "",
            )
            or ""
        ).strip()

        allowed_tools = _normalize_tools(
            _parse_allowed_tools(
                _first_non_empty(
                    frontmatter.get("allowed-tools"),
                    frontmatter.get("allowed_tools"),
                    metadata_map.get("allowed_tools"),
                    meta.get("allowed_tools"),
                    "",
                )
            )
        )

        template_path = item / "templates" / "output.md"
        output_template = template_path.read_text(encoding="utf-8").strip() if template_path.exists() else ""
        if not skill_doc:
            skill_doc = output_template

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
                compatibility=compatibility,
                allowed_tools=allowed_tools,
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
        skill_doc=definition.skill_doc,
        allowed_tools=_normalize_tools(definition.allowed_tools),
    )
