"""
Local MySQL MCP server over stdio.

Run (manual):
  cd backend
  python app/mcp/mysql_mcp_server.py
"""

from __future__ import annotations

import json
import os
import re
from contextlib import closing
from dotenv import load_dotenv
import pymysql
from mcp.server.fastmcp import FastMCP

load_dotenv()
mcp = FastMCP("mysql-stdio")

# print(os.getenv("MYSQL_MCP_PORT"))
# print(os.getenv("MYSQL_MCP_USERNAME"))
# print(os.getenv("MYSQL_MCP_PASSWORD"))
# print(os.getenv("MYSQL_MCP_DATABASE"))


def _db_config() -> dict:
    return {
        "host": os.getenv("MYSQL_MCP_HOST", os.getenv("MYSQL_HOST", "127.0.0.1")),
        "port": int(os.getenv("MYSQL_MCP_PORT", os.getenv("MYSQL_PORT", "3306"))),
        "user": os.getenv("MYSQL_MCP_USERNAME", os.getenv("MYSQL_USERNAME", "root")),
        "password": os.getenv("MYSQL_MCP_PASSWORD", os.getenv("MYSQL_PASSWORD", "123456")),
        "database": os.getenv("MYSQL_MCP_DATABASE", os.getenv("MYSQL_DATABASE", "")),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


def _query(sql: str, args: tuple | None = None) -> list[dict]:
    cfg = _db_config()
    with closing(pymysql.connect(**cfg)) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            rows = cur.fetchall()
            return list(rows or [])


def _list_tables() -> list[str]:
    rows = _query("SHOW TABLES;")
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = next((v for v in row.values() if isinstance(v, str) and v), None)
        if value:
            names.append(value)
    return names


def _normalize_table_name(query: str, tables: list[str]) -> str | None:
    text = (query or "").strip()
    if not text:
        return None

    table_map = {name.lower(): name for name in tables}
    patterns = [
        r"\b(?:table|from|describe|desc)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b",
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*表",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            found = table_map.get(m.group(1).lower())
            if found:
                return found

    identifiers = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", text, re.IGNORECASE)
    for item in identifiers:
        found = table_map.get(item.lower())
        if found:
            return found
    return None


def _is_table_list_intent(query: str) -> bool:
    text = (query or "").lower()
    return any(k in text for k in ("table", "tables", "list tables", "哪些表", "有哪些表", "表名"))


def _is_column_intent(query: str) -> bool:
    text = (query or "").lower()
    return any(k in text for k in ("字段", "列", "表结构", "column", "columns", "schema", "describe", "desc"))


@mcp.tool()
def mysql_list_tables(query: str = "") -> str:
    """列出当前数据所有表."""
    tables = _list_tables()
    return "tables: " + ", ".join(tables[:200]) if tables else "tables: (empty)"


@mcp.tool()
def mysql_search_schema(query: str) -> str:
    """根据用户问题查询表结构、字段、列信息."""
    tables = _list_tables()
    if not tables:
        return "No tables found in current database."

    if _is_table_list_intent(query):
        return "tables: " + ", ".join(tables[:200])

    table = _normalize_table_name(query, tables)
    if table and _is_column_intent(query):
        rows = _query(f"SHOW COLUMNS FROM `{table}`;")
        cols = []
        for row in rows:
            name = str(row.get("Field") or "").strip()
            col_type = str(row.get("Type") or "").strip()
            if name:
                cols.append(f"{name}({col_type})" if col_type else name)
        if cols:
            return f"{table} columns: " + ", ".join(cols[:200])
        return f"{table} columns: (empty)"

    preview: dict[str, list[str]] = {}
    for name in tables[:8]:
        rows = _query(f"SHOW COLUMNS FROM `{name}`;")
        preview[name] = [str(item.get("Field")) for item in rows if isinstance(item, dict) and item.get("Field")]
    return json.dumps({"tables": tables[:50], "preview": preview}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
