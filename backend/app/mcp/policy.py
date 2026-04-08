from contextvars import ContextVar

from app.config import MCP_SOURCE_ALLOWLIST, MCP_TOOL_ALLOWLIST

READONLY_DENY_KEYWORDS = (
    "add",
    "create",
    "update",
    "delete",
    "remove",
    "comment",
    "write",
    "post",
    "put",
    "patch",
    "fork",
    "execute",
    "run",
    "send",
    "merge",
    "approve",
)

SOURCE_ALIASES = {
    "git": ("git", "github", "gitlab", "repo", "commit", "pr"),
    "db": ("db", "database", "mysql", "postgres", "schema", "ddl", "table", "column", "index"),
    "log": ("log", "logs", "error", "traceback", "stack", "filelog"),
}

_MCP_ALLOWED_THIS_TURN: ContextVar[bool] = ContextVar("_MCP_ALLOWED_THIS_TURN", default=False)
_MCP_ALLOWED_SOURCES: ContextVar[set[str]] = ContextVar("_MCP_ALLOWED_SOURCES", default=set())


def _normalized_set(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def get_allowed_sources_from_config() -> set[str]:
    values = _normalized_set(MCP_SOURCE_ALLOWLIST)
    return values or {"git", "db", "log"}


def get_allowlisted_tool_names() -> set[str]:
    return _normalized_set(MCP_TOOL_ALLOWLIST)


def infer_source(tool_name: str, description: str = "") -> str | None:
    merged = f"{tool_name} {description}".lower()
    for source, keywords in SOURCE_ALIASES.items():
        if any(keyword in merged for keyword in keywords):
            return source
    return None


def is_readonly_tool(tool_name: str, description: str = "") -> bool:
    merged = f"{tool_name} {description}".lower()
    return not any(keyword in merged for keyword in READONLY_DENY_KEYWORDS)


def allow_tool(tool_name: str, description: str = "") -> tuple[bool, str | None]:
    allowlisted_names = get_allowlisted_tool_names()
    if allowlisted_names and tool_name.lower() not in allowlisted_names:
        return False, None

    if not is_readonly_tool(tool_name, description):
        return False, None

    source = infer_source(tool_name, description)
    if source is None:
        return False, None

    if source not in get_allowed_sources_from_config():
        return False, None
    return True, source


def set_turn_policy(allowed: bool, allowed_sources: list[str] | None = None) -> None:
    _MCP_ALLOWED_THIS_TURN.set(bool(allowed))
    source_set = {item.strip().lower() for item in (allowed_sources or []) if item and item.strip()}
    _MCP_ALLOWED_SOURCES.set(source_set)


def reset_turn_policy() -> None:
    _MCP_ALLOWED_THIS_TURN.set(False)
    _MCP_ALLOWED_SOURCES.set(set())


def can_call_source(source: str) -> bool:
    if not _MCP_ALLOWED_THIS_TURN.get():
        return False
    configured = get_allowed_sources_from_config()
    per_turn = _MCP_ALLOWED_SOURCES.get()
    source = (source or "").strip().lower()
    if source not in configured:
        return False
    if per_turn and source not in per_turn:
        return False
    return True
