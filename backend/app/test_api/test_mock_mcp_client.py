"""
Mock MCP client integration check.

Usage (uv environment):
  cd backend
  uv run python app/test_api/test_mock_mcp_client.py
"""
import asyncio

from app.agent import rebuild_agent_with_external_tools
from app.mcp.client_manager import mcp_client_manager


async def main() -> None:
    await mcp_client_manager.initialize()
    print("mcp_enabled:", mcp_client_manager.enabled)
    print("mcp_sources:", mcp_client_manager.available_sources())
    print("agent_external_tools:", rebuild_agent_with_external_tools())

    git_items = mcp_client_manager.query_git("latest commits")
    print("git_result_count:", len(git_items))
    if git_items:
        print("git_sample:", git_items[0]["summary"][:120])

    items = mcp_client_manager.query_mysql("list mysql tables")
    print("mysql_result_count:", len(items))
    if items:
        print("mysql_sample:", items[0]["summary"][:120])


if __name__ == "__main__":
    asyncio.run(main())
