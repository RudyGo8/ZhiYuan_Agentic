---
name: mcp_integration
description: 当用户要求给当前 Agentic RAG 项目添加、配置、调试 MCP Server 时使用
version: 0.1.0
---

# MCP Integration Skill for Agentic RAG

## 适用场景
用户要求给当前项目接入新的 MCP Server。

## 执行流程
1. 判断 MCP Server 类型：stdio / SSE / HTTP / WebSocket。
2. 判断是否需要环境变量。
3. 检查项目当前 MCP 配置结构。
4. 生成 MCP Server 配置。
5. 注册到 mcp_client_manager。
6. 校验连接和工具发现。
7. 输出配置说明和启动方式。

## 安全规则
- 不硬编码 API Key。
- API Key 使用环境变量。
- 不自动覆盖已有 MCP 配置。
- 修改前先读取现有配置。