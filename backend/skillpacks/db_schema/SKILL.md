---
name: db-schema
description: Analyze MySQL table schema, columns, indexes and relationships. Use when the user asks database/table/column/DDL questions.
compatibility: Requires MCP mysql source when available.
metadata:
  display_name: 数据库字段分析
use-mcp: true
mcp-sources:
  - mysql
keywords:
  - 数据库
  - 表
  - 字段
  - 列
  - 索引
  - 主键
  - 外键
  - schema
  - ddl
  - sql
  - mysql
priority: 100
allowed-tools: search_knowledge_base mcp_search_mysql
---

# 数据库字段分析

## 使用规则
1. 优先基于 `mysql` 实时结果给结论。
2. 如果证据不足，不要臆测字段含义，明确说明限制。
3. 如果用户提供 SQL，先识别涉及表和字段，再解释关系与作用。

## 输出结构
1. 涉及表
2. 涉及字段
3. 字段作用说明
4. 表之间关系
5. 结论
