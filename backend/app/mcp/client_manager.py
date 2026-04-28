import importlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from app.config import MCP_ENABLED, MCP_SERVERS_JSON, logger

_MCP_IMPORT_ERROR: str | None = None


def _import_multi_server_mcp_client():
    """
    避免本地 app/mcp 包和第三方 mcp 包命名冲突。
    """
    app_dir = Path(__file__).resolve().parents[1]
    original_sys_path = list(sys.path)

    loaded_mcp = sys.modules.get("mcp")
    loaded_mcp_file = getattr(loaded_mcp, "__file__", "") if loaded_mcp else ""

    if loaded_mcp_file:
        try:
            if Path(loaded_mcp_file).resolve().is_relative_to(app_dir):
                sys.modules.pop("mcp", None)
        except OSError:
            pass

    try:
        sys.path = [
            p for p in sys.path
            if Path(p or ".").resolve() != app_dir
        ]
        module = importlib.import_module("langchain_mcp_adapters.client")
        return module.MultiServerMCPClient
    finally:
        sys.path = original_sys_path


try:
    MultiServerMCPClient = _import_multi_server_mcp_client()
except Exception:
    MultiServerMCPClient = None
    _MCP_IMPORT_ERROR = traceback.format_exc()


class MCPClientManager:
    def __init__(self):
        self._initialized = False
        self._enabled = False
        self._init_error: str | None = None
        self._agent_tools: list[Any] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def init_error(self) -> str | None:
        return self._init_error

    async def initialize(self) -> None:
        if self._initialized:
            return

        self._initialized = True

        if not MCP_ENABLED:
            self._init_error = "MCP disabled by MCP_ENABLED=false"
            logger.info(self._init_error)
            return

        client_class = self._get_client_class()
        if client_class is None:
            return

        servers = self._load_servers()
        if not servers:
            return

        raw_tools: list[Any] = []

        for server_name, server_cfg in servers.items():
            try:
                client = client_class({server_name: server_cfg})
                tools = await client.get_tools()
                raw_tools.extend(tools)

                logger.info(
                    "MCP server loaded: server=%s tools=%s",
                    server_name,
                    [getattr(tool, "name", "unknown") for tool in tools],
                )

            except Exception as exc:
                logger.warning(
                    "MCP server init failed: server=%s err=%s",
                    server_name,
                    exc,
                )

        # 最小自主模式：MCP Server 暴露什么工具，就全部交给 Agent
        self._agent_tools = raw_tools
        self._enabled = bool(self._agent_tools)

        if not self._enabled:
            self._init_error = "no MCP tools available"

        logger.info(
            "MCP initialized. enabled=%s tools=%s",
            self._enabled,
            [getattr(tool, "name", "unknown") for tool in self._agent_tools],
        )

    async def get_agent_tools(self) -> list[Any]:
        """
        返回所有 MCP 原始工具，直接交给 Agent 自主调用。
        """
        await self.initialize()
        return list(self._agent_tools)

    def tool_names(self) -> list[str]:
        return [
            str(getattr(tool, "name", "unknown"))
            for tool in self._agent_tools
        ]

    def _get_client_class(self):
        global MultiServerMCPClient, _MCP_IMPORT_ERROR

        if MultiServerMCPClient is not None:
            return MultiServerMCPClient

        try:
            MultiServerMCPClient = _import_multi_server_mcp_client()
            _MCP_IMPORT_ERROR = None
            return MultiServerMCPClient

        except Exception:
            _MCP_IMPORT_ERROR = traceback.format_exc()
            detail = (
                (_MCP_IMPORT_ERROR or "").strip().splitlines()[-1]
                if _MCP_IMPORT_ERROR
                else "unknown error"
            )
            self._init_error = f"langchain-mcp-adapters import failed: {detail}"
            logger.warning("MCP disabled: %s", self._init_error)
            return None

    def _load_servers(self) -> dict[str, Any] | None:
        if not MCP_SERVERS_JSON.strip():
            self._init_error = "MCP_SERVERS_JSON is empty"
            logger.warning("MCP disabled: %s", self._init_error)
            return None

        try:
            servers = json.loads(MCP_SERVERS_JSON)

            if not isinstance(servers, dict) or not servers:
                raise ValueError("MCP_SERVERS_JSON must be a non-empty JSON object")

            return self._normalize_servers(self._expand_env_vars(servers))

        except Exception as exc:
            self._init_error = f"invalid MCP_SERVERS_JSON: {exc}"
            logger.warning("MCP disabled: %s", self._init_error)
            return None

    @staticmethod
    def _normalize_servers(servers: dict[str, Any]) -> dict[str, Any]:
        """
        处理 Windows / 虚拟环境 / 相对路径问题。
        """
        backend_root = Path(__file__).resolve().parents[2]
        output: dict[str, Any] = {}

        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                output[name] = cfg
                continue

            item = dict(cfg)

            if str(item.get("transport", "")).strip().lower() == "stdio":
                cmd = str(item.get("command", "")).strip().lower()

                if cmd in {"python", "python3"}:
                    item["command"] = sys.executable

                args = item.get("args")
                if isinstance(args, list):
                    item["args"] = [
                        str((backend_root / arg).resolve())
                        if isinstance(arg, str)
                        and arg.endswith(".py")
                        and not Path(arg).is_absolute()
                        else arg
                        for arg in args
                    ]

            output[name] = item

        return output

    @staticmethod
    def _expand_env_vars(value: Any) -> Any:
        if isinstance(value, str):
            for key, val in os.environ.items():
                value = value.replace(f"${{{key}}}", val)
            return value

        if isinstance(value, dict):
            return {
                k: MCPClientManager._expand_env_vars(v)
                for k, v in value.items()
            }

        if isinstance(value, list):
            return [
                MCPClientManager._expand_env_vars(v)
                for v in value
            ]

        return value


mcp_client_manager = MCPClientManager()