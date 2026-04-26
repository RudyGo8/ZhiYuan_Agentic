---
name: git-analysis
description: Analyze repository changes, commits and impact scope. Use when user asks what changed, where code is implemented, or impact of commits/PRs.
compatibility: Requires MCP git source when available.
metadata:
  display_name: 代码变更分析
use-mcp: true
mcp-sources:
  - git
keywords:
  - 提交
  - 变更
  - 改动
  - 代码改动
  - 最近改了什么
  - 哪个文件
  - 仓库
  - 分支
  - pr
  - commit
  - diff
  - repo
  - github
  - gitlab
priority: 95
allowed-tools: search_knowledge_base mcp_search_git
---

# 代码变更分析

## 使用规则
1. 先说明“改了哪些文件/模块”，再说明“改了什么”和“可能影响什么”。
2. 对最近变更问题，优先关注最近提交。
3. 没有证据时不要凭空推断实现细节。

## 输出结构
1. 涉及仓库/目录
2. 关键文件
3. 主要变更内容
4. 可能影响的模块或流程
5. 结论
