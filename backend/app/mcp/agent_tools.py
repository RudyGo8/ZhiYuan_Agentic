from app.mcp.client_manager import mcp_client_manager
from app.mcp.policy import can_call_source, can_call_tool
from app.tools.runtime import emit_rag_step


def _search_source(source: str, query: str) -> str:
    tool_name = f"mcp_search_{(source or '').strip().lower()}"
    query = (query or "").strip()
    if not query:
        return "query is required."
    if not mcp_client_manager.enabled:
        return "MCP is not available in current environment."
    if not can_call_tool(tool_name):
        return f"MCP tool '{tool_name}' is disabled for this request."
    if not can_call_source(source):
        return f"MCP source '{source}' is disabled for this request."

    emit_rag_step("🔎", f"查询外部来源: {source}", query[:60])
    items = mcp_client_manager.query_source(source, query)
    if not items:
        return f"No external results from {source}."

    blocks = []
    for idx, item in enumerate(items, 1):
        blocks.append(f"[{idx}] ({item.get('tool_name')})\n{item.get('summary', '')}")
    return "\n\n---\n\n".join(blocks)


def mcp_search_git(query: str) -> str:
    """Search read-only git/github context via MCP tools."""
    return _search_source("git", query)


def mcp_search_mysql(query: str) -> str:
    """Search read-only MySQL schema context via MCP tools."""
    return _search_source("mysql", query)


SOURCE_TO_TOOL = {
    "git": mcp_search_git,
    "mysql": mcp_search_mysql,
}


def get_enabled_mcp_tools() -> list:
    return [SOURCE_TO_TOOL[source] for source in mcp_client_manager.available_sources() if source in SOURCE_TO_TOOL]
