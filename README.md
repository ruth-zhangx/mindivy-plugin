# Mindivy Plugin Marketplace

Official Mindivy plugin for Claude Code — grounded research and co-creation against your Mindivy knowledge base.

## What's inside

| Plugin | Description |
|--------|-------------|
| `mindivy` | `/mindivy:research` (knowledge-base-grounded research), `/mindivy:draft-chapter` (chapter co-writing), SessionStart workspace digest, bundled mindivy-mcp server config. |

## Install

Requires Claude Code ≥ 1.0.33.

```
/plugin marketplace add ruth-zhangx/mindivy-plugin
/plugin install mindivy@mindivy-official
```

**China mirror (Gitee):**

```
/plugin marketplace add https://gitee.com/ruth-zhangx/mindivy-plugin
/plugin install mindivy@mindivy-official
```

## Prerequisites

- The Mindivy desktop app with your knowledge base (`~/.mindivy` workspace state) for the SessionStart digest and MCP server.
