import asyncio
import json
import os
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

from app.config import MCP_ENABLED, MCP_MAX_TOOLS_PER_SOURCE, MCP_SERVERS_JSON, MCP_TOOL_TIMEOUT_SECONDS, logger
from app.mcp.tool_registry import MCPToolEntry, build_registry
from app.mcp.trace import append_mcp_trace, new_mcp_call

_MCP_IMPORT_ERROR: str | None = None
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except Exception:  # pragma: no cover - 可选依赖
    MultiServerMCPClient = None
    _MCP_IMPORT_ERROR = traceback.format_exc()


class MCPClientManager:
    def __init__(self):
        self._initialized = False
        self._enabled = False
        self._registry: dict[str, list[MCPToolEntry]] = {}
        self._init_error: str | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def init_error(self) -> str | None:
        return self._init_error

    def available_sources(self) -> list[str]:
        return sorted(self._registry.keys())

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        if not MCP_ENABLED:
            logger.info("MCP client layer disabled by MCP_ENABLED=false")
            return

        global MultiServerMCPClient, _MCP_IMPORT_ERROR
        if MultiServerMCPClient is None:
            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient as _MSC
                MultiServerMCPClient = _MSC
                _MCP_IMPORT_ERROR = None
            except Exception:
                _MCP_IMPORT_ERROR = traceback.format_exc()

        if MultiServerMCPClient is None:
            detail = (_MCP_IMPORT_ERROR or "").strip().splitlines()[-1] if _MCP_IMPORT_ERROR else ""
            self._init_error = f"langchain-mcp-adapters import failed: {detail or 'unknown error'}"
            logger.warning("MCP client layer disabled: %s", self._init_error)
            return

        if not MCP_SERVERS_JSON.strip():
            self._init_error = "MCP_SERVERS_JSON is empty"
            logger.warning("MCP client layer disabled: %s", self._init_error)
            return

        try:
            servers = json.loads(MCP_SERVERS_JSON)
            if not isinstance(servers, dict) or not servers:
                raise ValueError("MCP_SERVERS_JSON must be a non-empty JSON object")
            servers = self._expand_env_vars(servers)
            self._validate_servers(servers)
            servers = self._normalize_servers(servers)
        except Exception as exc:
            self._init_error = f"invalid MCP_SERVERS_JSON: {exc}"
            logger.warning("MCP client layer disabled: %s", self._init_error)
            return

        raw_tools: list[Any] = []
        failed_servers: dict[str, str] = {}
        for server_name, server_cfg in servers.items():
            try:
                client = MultiServerMCPClient({server_name: server_cfg})
                tools = await client.get_tools()
                raw_tools.extend(tools)
            except Exception as exc:  # pragma: no cover - 外部集成异常
                failed_servers[server_name] = str(exc)
                logger.warning("MCP server init failed: server=%s err=%s", server_name, exc)

        self._registry = build_registry(raw_tools)
        self._enabled = bool(self._registry)

        logger.info(
            "MCP client initialized. enabled=%s sources=%s tools=%s",
            self._enabled,
            list(self._registry.keys()),
            sum(len(v) for v in self._registry.values()),
        )
        if failed_servers:
            logger.warning("MCP partial init failures: %s", failed_servers)

        if not self._enabled:
            if failed_servers:
                self._init_error = f"all MCP servers failed or no allowed tools: {failed_servers}"
            else:
                self._init_error = "no readonly tools available after policy filtering"

    def query_source(self, source: str, query: str, max_tools: int | None = None) -> list[dict[str, Any]]:
        source = (source or "").strip().lower()
        query = (query or "").strip()
        entries = self._registry.get(source, [])
        if not query:
            return []
        if not self._enabled or not entries:
            return []

        limit = max(1, int(max_tools)) if max_tools is not None else max(1, MCP_MAX_TOOLS_PER_SOURCE)
        selected = self._rank_entries_for_query(source, query, entries)[:limit]
        output: list[dict[str, Any]] = []

        for entry in selected:
            start = time.perf_counter()
            success = False
            error: str | None = None
            summary = ""
            try:
                raw = self._invoke_tool_with_timeout(entry.tool, query, MCP_TOOL_TIMEOUT_SECONDS)
                summary = self._summarize(raw)
                success = True
            except Exception as exc:
                error = str(exc)

            duration_ms = int((time.perf_counter() - start) * 1000)
            append_mcp_trace(
                new_mcp_call(
                    server_name=source,
                    tool_name=entry.name,
                    query=query,
                    success=success,
                    duration_ms=duration_ms,
                    result_summary=summary[:500],
                    error=error,
                )
            )

            if success and summary:
                output.append({"source": source, "tool_name": entry.name, "summary": summary})
        return output

    @staticmethod
    def _invoke_tool_with_timeout(tool_obj: Any, query: str, timeout_seconds: float) -> Any:
        tool_name = str(getattr(tool_obj, "name", "")).strip().lower()
        effective_timeout = max(0.1, float(timeout_seconds))
        if tool_name in {"list_commits", "search_commits"}:
            effective_timeout = max(effective_timeout, 25.0)

        result: dict[str, Any] = {}
        error: dict[str, Exception] = {}

        def _runner() -> None:
            try:
                result["value"] = MCPClientManager._invoke_tool(tool_obj, query)
            except Exception as exc:  # pragma: no cover - 透传异常
                error["exc"] = exc

        worker = threading.Thread(target=_runner, daemon=True)
        worker.start()
        worker.join(timeout=effective_timeout)
        if worker.is_alive():
            raise TimeoutError(f"Tool {getattr(tool_obj, 'name', 'unknown')} timed out after {effective_timeout:.1f}s")
        if "exc" in error:
            raise error["exc"]
        return result.get("value")

    @staticmethod
    def _invoke_tool(tool_obj: Any, query: str) -> Any:
        attempts: list[Any] = []

        parsed_repo = MCPClientManager._parse_github_repo(query)
        if not parsed_repo and MCPClientManager._tool_requires_repo(tool_obj):
            parsed_repo = MCPClientManager._get_default_repo()
        if parsed_repo:
            owner, repo = parsed_repo
            attempts.extend(
                [
                    {"owner": owner, "repo": repo, "perPage": 50},
                    {"owner": owner, "repo": repo},
                ]
            )

        attempts.extend(
            [
                {"query": query},
                {"q": query},
                {"keyword": query},
                {"text": query},
                {"input": query},
                {"question": query},
            ]
        )

        attempt_errors: list[Exception] = []
        ainvoke = getattr(tool_obj, "ainvoke", None)
        if callable(ainvoke):
            for args in attempts:
                try:
                    return MCPClientManager._run_coro(ainvoke(args))
                except Exception as exc:
                    attempt_errors.append(exc)
            if MCPClientManager._tool_accepts_string_input(tool_obj):
                return MCPClientManager._run_coro(ainvoke(query))
            if attempt_errors:
                raise attempt_errors[-1]
            raise RuntimeError(f"Tool {getattr(tool_obj, 'name', 'unknown')} invoke failed")

        invoke = getattr(tool_obj, "invoke", None)
        if callable(invoke):
            for args in attempts:
                try:
                    return invoke(args)
                except Exception as exc:
                    attempt_errors.append(exc)
            if MCPClientManager._tool_accepts_string_input(tool_obj):
                return invoke(query)
            if attempt_errors:
                raise attempt_errors[-1]
            raise RuntimeError(f"Tool {getattr(tool_obj, 'name', 'unknown')} invoke failed")

        raise RuntimeError(f"Tool {getattr(tool_obj, 'name', 'unknown')} has no invoke method")

    @staticmethod
    def _summarize(raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw.strip()[:1200]
        try:
            return json.dumps(raw, ensure_ascii=False)[:1200]
        except Exception:
            return str(raw)[:1200]

    @staticmethod
    def _run_coro(coro: Any) -> Any:
        try:
            asyncio.get_running_loop()
            in_event_loop = True
        except RuntimeError:
            in_event_loop = False

        if not in_event_loop:
            return asyncio.run(coro)

        result: dict[str, Any] = {}
        error: dict[str, Exception] = {}

        def _runner() -> None:
            try:
                result["value"] = asyncio.run(coro)
            except Exception as exc:  # pragma: no cover - 透传异常
                error["exc"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if "exc" in error:
            raise error["exc"]
        return result.get("value")

    @staticmethod
    def _normalize_servers(servers: dict[str, Any]) -> dict[str, Any]:
        backend_root = Path(__file__).resolve().parents[2]
        output: dict[str, Any] = {}

        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                output[name] = cfg
                continue

            item = dict(cfg)
            transport = str(item.get("transport", "")).strip().lower()
            if transport == "stdio":
                cmd = str(item.get("command", "")).strip().lower()
                if cmd in {"python", "python3"}:
                    item["command"] = sys.executable

                args = item.get("args")
                if isinstance(args, list):
                    fixed_args = []
                    for arg in args:
                        if isinstance(arg, str) and arg.endswith(".py"):
                            p = Path(arg)
                            if not p.is_absolute():
                                candidate = (backend_root / p).resolve()
                                if candidate.exists():
                                    arg = str(candidate)
                                else:
                                    fallback = (backend_root / "app" / "test_api" / p.name).resolve()
                                    if fallback.exists():
                                        arg = str(fallback)
                        fixed_args.append(arg)
                    item["args"] = fixed_args

            output[name] = item
        return output

    @staticmethod
    def _expand_env_vars(value: Any) -> Any:
        pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
        if isinstance(value, str):
            return pattern.sub(lambda m: os.getenv(m.group(1), ""), value)
        if isinstance(value, dict):
            return {k: MCPClientManager._expand_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [MCPClientManager._expand_env_vars(v) for v in value]
        return value

    @staticmethod
    def _validate_servers(servers: dict[str, Any]) -> None:
        for server_name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue

            transport = str(cfg.get("transport", "")).strip().lower()
            url = str(cfg.get("url", "")).strip()
            headers = cfg.get("headers") if isinstance(cfg.get("headers"), dict) else {}
            auth = str(headers.get("Authorization", "")).strip() if headers else ""

            if "http" in transport and not url:
                raise ValueError(f"server '{server_name}' missing url for transport '{transport}'")

            if "githubcopilot.com" in url.lower():
                if not auth:
                    raise ValueError(f"server '{server_name}' missing Authorization header")
                if auth.lower() in {"bearer", "bearer none", "none"}:
                    raise ValueError(f"server '{server_name}' has empty/invalid bearer token")

    @staticmethod
    def _parse_github_repo(query: str) -> tuple[str, str] | None:
        text = (query or "").strip()
        if not text:
            return None

        m = re.search(r"https?://github\.com/([^/\s]+)/([^/\s]+)", text, re.IGNORECASE)
        if m:
            owner = m.group(1).strip()
            repo = m.group(2).strip()
            repo = repo[:-4] if repo.lower().endswith(".git") else repo
            if owner and repo:
                return owner, repo

        m = re.search(r"\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b", text)
        if m:
            owner = m.group(1).strip()
            repo = m.group(2).strip()
            if owner.lower() not in {"http", "https", "github"} and repo.lower() not in {"com"}:
                return owner, repo
        return None

    @staticmethod
    def _get_default_repo() -> tuple[str, str] | None:
        slug = (os.getenv("GITHUB_DEFAULT_REPO") or "").strip()
        if "/" in slug:
            owner, repo = slug.split("/", 1)
            owner = owner.strip()
            repo = repo.strip()
            if owner and repo:
                return owner, repo

        owner = (os.getenv("GITHUB_DEFAULT_OWNER") or "").strip()
        repo = (os.getenv("GITHUB_DEFAULT_REPO_NAME") or "").strip()
        if owner and repo:
            return owner, repo
        return None

    @staticmethod
    def _extract_schema_payload(tool_obj: Any) -> dict[str, Any] | None:
        schema = getattr(tool_obj, "args_schema", None)
        if isinstance(schema, dict):
            return schema
        if schema is not None and hasattr(schema, "model_json_schema"):
            try:
                payload = schema.model_json_schema()
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass
        return None

    @staticmethod
    def _tool_requires_repo(tool_obj: Any) -> bool:
        payload = MCPClientManager._extract_schema_payload(tool_obj)
        if not payload:
            return False
        required = payload.get("required") or []
        required_set = {str(item).strip().lower() for item in required}
        return "owner" in required_set and "repo" in required_set

    @staticmethod
    def _tool_accepts_string_input(tool_obj: Any) -> bool:
        payload = MCPClientManager._extract_schema_payload(tool_obj)
        if not payload:
            return True
        return str(payload.get("type", "")).strip().lower() != "object"

    @staticmethod
    def _rank_entries_for_query(source: str, query: str, entries: list[MCPToolEntry]) -> list[MCPToolEntry]:
        text = (query or "").lower()
        repo_known = (
            MCPClientManager._parse_github_repo(query) is not None
            or MCPClientManager._get_default_repo() is not None
        )
        has_sha = re.search(r"\b[0-9a-f]{7,40}\b", text) is not None

        def score(entry: MCPToolEntry) -> int:
            name = (entry.name or "").lower()
            desc = (entry.description or "").lower()
            merged = f"{name} {desc}"
            s = 0

            if any(k in name for k in ("list_", "get_", "search_")):
                s += 10
            if any(k in merged for k in ("add ", " add_", " create", " update", " delete", " remove", " fork", " comment")):
                s -= 200

            if source == "git":
                commit_intent = any(k in text for k in ("提交", "变更", "commit", "commits", "changelog", "changes"))
                pr_intent = any(k in text for k in ("pr", "pull request", "合并请求"))
                issue_intent = any(k in text for k in ("issue", "缺陷", "bug"))

                if repo_known and not pr_intent and not issue_intent and name == "list_commits":
                    s += 1200
                if commit_intent and name == "list_commits":
                    s += 500
                elif commit_intent and (name == "search_commits" or "commit" in name):
                    s += 120
                if name == "get_commit" and not has_sha:
                    s -= 300
                if pr_intent and ("pull" in name or "pr" in name):
                    s += 220
                if issue_intent and "issue" in name:
                    s += 180

            if source == "mysql":
                db_intent = any(k in text for k in ("数据库", "表", "字段", "列", "索引", "外键", "schema", "ddl", "sql"))
                if db_intent and any(k in merged for k in ("schema", "table", "column", "field", "index", "ddl", "sql")):
                    s += 260
                if db_intent and any(k in name for k in ("list_", "get_", "search_")):
                    s += 80

            return s

        return sorted(entries, key=score, reverse=True)


mcp_client_manager = MCPClientManager()
