# mindivy — Claude Code Plugin

T186：Mindivy 共创工作流分发载体。安装一次即得：知识库检索（MCP 5 工具）+ 两个共创命令 + SessionStart 工作区状态注入。

## 组件

| 组件 | 路径 | 作用 |
|---|---|---|
| `/mindivy:research` | `commands/research.md` | 知识库接地检索：双路径检索 → 技能格式引用综合 |
| `/mindivy:draft-chapter` | `commands/draft-chapter.md` | 共创草稿：检索先行 → 提提纲 → 逐节起草 + 全程引用 |
| SessionStart hook | `hooks/hooks.json` + `hooks/session_start.py` | 注入工作区状态（最近 checkpoint + 未完成任务计数）。H10 模式：只读、幂等、恒 exit 0。解析序：`$MINDIVY_REPO` → repo 向上探测 → `~/.mindivy/workspace-state.md`（app 写入——T192：最近文档/活跃 AI 任务/知识库统计，vault 锁定时清空） |
| MCP server 配置 | `.mcp.json` + `servers/mindivy-mcp.sh` | 新装路径：解析 venv/python → 读 token → 设 PYTHONPATH → 启动 `mindivy_mcp` |

**SKILL.md 不随插件分发** — `mindivy` 技能单一来源在 app 侧
（`python-service/mindivy_mcp/skill/SKILL.md`），经 app 内
Settings → External Agent Access → "Install skill" 安装到
`~/.claude/skills/mindivy/SKILL.md`（sha256 自校验 + 永不覆盖用户修改）。
插件命令按名称引用该技能。理由：Claude Code 用户级 skill 优先级高于插件同名
skill（插件版永不加载）。

## 环境变量

以下变量是 **wrapper 的 shell 环境覆盖项**（用户自行在 shell/启动器里设置时生效）。注意：它们**不进 `.mcp.json`**——Claude Code 不展开插件 `.mcp.json` 的 `env` 值（G086），写占位符只会把字面量字符串传给 wrapper。

| 变量 | 作用 | 默认 |
|---|---|---|
| `MCP_TOKEN` | MCP 认证 token（缺省时 wrapper 读 `~/.mindivy/mcp_token`） | 无 |
| `MINDIVY_REPO` | Mindivy 仓库路径（dev 机 venv/PYTHONPATH 解析 + SessionStart repo 探测首选） | 无（SessionStart 自动向上探测） |
| `MINDIVY_PYTHON` | 覆盖 python 解析（须可执行） | 无 |
| `MINDIVY_BACKEND_URL` | Mindivy 后端地址 | `http://127.0.0.1:8000` |

## Troubleshooting

| 症状 | 原因 | 处理 |
|---|---|---|
| `claude mcp list` 显示 mindivy 未连接 | token 缺失 / python 未找到 | wrapper stderr 有行动指引；确认 app 运行过一次 + `~/.mindivy/mcp_token` 存在 |
| 工具调用返回 "The Mindivy backend is not reachable"（后端明明健康） | v0.1.0 的 `.mcp.json` env 占位符字面量（G086） | 更新插件至 v0.1.1（env 块已删），重启 Claude Code session 使新配置生效 |
| 已有用户级 `mcpServers.mindivy` 时插件配置无效 | 优先级 local > project > user > plugin（预期） | 无需处理；用户级条目退役可选 |
| SessionStart 注入的上下文交互模式下不可见 | 上游已知回归 [#45438](https://github.com/anthropics/claude-code/issues/45438)（插件 SessionStart additionalContext 被静默丢弃）。**2026-08-15 实测交互模式注入可见**（可能已修复或间歇性） | 用 `claude --print` 验证；继续观察 |
| `/mindivy:research` 提示未找到 skill | skill 未从 app 安装 | app Settings → External Agent Access → Install skill |

## 开发

- 校验：`claude plugin validate /home/dell/mindivy/plugins/mindivy`
- 单测：`python3 -m pytest tests/test_session_start_digest.py`（仓库根，digest 构建器）
- wrapper 冒烟：`MINDIVY_REPO=/home/dell/mindivy MCP_TOKEN=x bash servers/mindivy-mcp.sh` 管道 JSON-RPC initialize
