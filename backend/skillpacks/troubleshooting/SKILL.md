---
name: troubleshooting
description: Troubleshoot failures, abnormal status, empty results, and regressions. Use when user asks why something failed and asks for evidence-based diagnosis.
compatibility: Requires MCP mysql/git sources when available.
metadata:
  display_name: 故障排查
use-mcp: true
mcp-sources:
  - mysql
  - git
keywords:
  - 报错
  - 错误
  - 失败
  - 异常
  - 排查
  - 原因
  - error
  - fail
  - failed
  - bug
  - issue
priority: 110
allowed-tools: search_knowledge_base mcp_search_mysql mcp_search_git
---

# 故障排查

## 使用规则
1. 先定义问题现象，再给原因假设，不要跳结论。
2. 需要实时证据时，优先查询 `mysql` 和 `git`。
3. 若证据不足，明确说明“当前结论为假设”。

## 输出结构
1. 问题现象
2. 可能原因
3. 已有证据
4. 建议排查步骤
5. 初步结论
