'''
@create_time: 2026/4/28 上午1:02
@Author: GeChao
@File: test_project.py
'''


import asyncio

from app.tools.project_tools import (
    ProjectFileReaderTool,
    ProjectCodeEditorTool,
    ProjectShellTool,
)


async def main():
    context = {
        "project_root": r"F:\AI_Models\DEMO\My_Demo\2.Rag_Agent\backend",
        "validate_command": "python -m compileall app",
    }

    print("===== 测试 ProjectFileReaderTool =====")
    reader = ProjectFileReaderTool()
    reader_result = await reader.run(context)
    print(reader_result.keys())

    print("\n===== 测试 ProjectCodeEditorTool =====")
    editor = ProjectCodeEditorTool()
    editor_result = await editor.run(context)
    print(editor_result)

    print("\n===== 测试 ProjectShellTool =====")
    shell = ProjectShellTool()
    shell_result = await shell.run(context)
    print(shell_result)


if __name__ == "__main__":
    asyncio.run(main())