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

    for source in ("db", "git"):
        items = mcp_client_manager.query_source(source, "payment api latest status")
        print(f"{source}_result_count:", len(items))
        if items:
            print(f"{source}_sample:", items[0]["summary"][:120])


if __name__ == "__main__":
    asyncio.run(main())
