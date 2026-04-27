'''
@create_time: 2026/4/28 上午12:24
@Author: GeChao
@File: project_tools.py
'''

from pathlib import Path
import subprocess


class ProjectFileReaderTool:
    name = "project_file_reader"

    async def run(self, context: dict, step=None):
        project_root = Path(context["project_root"])

        target_files = [
            ".env.example",
            ".mcp.json",
            "app/mcp/client_manager.py",
            "app/config.py",
            "pyproject.toml",
        ]

        result = {}

        for file in target_files:
            path = project_root / file

            if path.exists() and path.is_file():
                result[file] = path.read_text(encoding="utf-8")

        return result


class ProjectCodeEditorTool:
    name = "project_code_editor"

    async def run(self, context: dict, step=None):
        return {
            "mode": "dry_run",
            "message": "第一版暂不直接写入文件，只生成修改建议。",
            "suggested_changes": [
                "检查是否已有 MCP 配置文件",
                "新增或更新 MCP Server 配置",
                "检查 .env 中是否需要新增 API Key",
                "检查 mcp_client_manager 是否需要注册新 Server",
            ],
        }


class ProjectShellTool:
    name = "project_shell"

    SAFE_COMMANDS = {
        "python -m compileall app",
        "python -m pytest",
    }

    async def run(self, context: dict, step=None):
        project_root = context["project_root"]
        command = context.get("validate_command", "python -m compileall app")

        if command not in self.SAFE_COMMANDS:
            return {
                "error": "命令不在安全白名单中",
                "command": command,
            }

        result = subprocess.run(
            command,
            cwd=project_root,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
