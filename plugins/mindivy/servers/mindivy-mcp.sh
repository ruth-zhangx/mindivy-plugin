#!/usr/bin/env bash
# ---
# @status: active
# @kind: Operator
# @input: env (MCP_TOKEN/MINDIVY_REPO/MINDIVY_PYTHON/MINDIVY_BACKEND_URL) + MCP stdio on fd 0/1
# @output: mindivy_mcp server process (stdio MCP)
# @side_effects: none (reads ~/.mindivy/mcp_token — never writes there, G075)
# @description: T186 fresh-install MCP launcher. Resolves repo (venv + PYTHONPATH anchor),
#   python, and the MCP token, then execs `python -m mindivy_mcp`. Path anchoring (G076/G077):
#   repo resolves from MINDIVY_REPO env, else from the script's own path (local-dir marketplace
#   installs keep the plugin in-repo — cache-copied installs rely on the env vars). Never cwd.
#   Fail-fast with actionable stderr (MCP startup failures surface in `claude mcp list`).
# ---
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_REPO="$(cd "$SCRIPT_DIR/../../.." && pwd 2>/dev/null || true)"

# 1. Resolve repo (anchor for venv + PYTHONPATH): MINDIVY_REPO → script-own-path → none.
#    Script-own-path works because local-dir marketplaces keep the plugin at its source path;
#    if a marketplace form copies the plugin to a cache dir, CLAUDE.md won't exist there and
#    resolution falls through to the env vars / PATH python.
REPO=""
if [ -n "${MINDIVY_REPO:-}" ] && [ -d "$MINDIVY_REPO/python-service" ]; then
  REPO="$(cd "$MINDIVY_REPO" && pwd)"
elif [ -n "${SCRIPT_REPO:-}" ] && [ -f "$SCRIPT_REPO/CLAUDE.md" ] && [ -x "$SCRIPT_REPO/python-service/.venv/bin/python" ]; then
  REPO="$SCRIPT_REPO"
fi

# 2. Resolve python: $MINDIVY_PYTHON → repo venv → PATH python3
PYTHON=""
if [ -n "${MINDIVY_PYTHON:-}" ] && [ -x "$MINDIVY_PYTHON" ]; then
  PYTHON="$MINDIVY_PYTHON"
elif [ -n "$REPO" ]; then
  PYTHON="$REPO/python-service/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
fi

if [ -z "$PYTHON" ]; then
  echo "mindivy-mcp: no python found. Set MINDIVY_PYTHON or MINDIVY_REPO (repo with python-service/.venv), or install python3." >&2
  exit 1
fi

# 3. PYTHONPATH so the mindivy_mcp package resolves without pip install (G076: CLI ignores cwd)
PYTHONPATH=""
if [ -n "$REPO" ]; then
  PYTHONPATH="$REPO/python-service"
else
  # venv-derived repo: venv sits at <repo>/python-service/.venv
  case "$PYTHON" in
    */python-service/.venv/bin/python*)
      PYTHONPATH="$(dirname "$(dirname "$(dirname "$(dirname "$PYTHON")")")")"
      ;;
  esac
fi

# 4. Token: $MCP_TOKEN → first line of ~/.mindivy/mcp_token (app writes it, chmod 600).
#    Read-only here — never recreate/move anything in ~/.mindivy (G075).
MCP_TOKEN="${MCP_TOKEN:-}"
if [ -z "$MCP_TOKEN" ] && [ -r "$HOME/.mindivy/mcp_token" ]; then
  MCP_TOKEN="$(head -n 1 "$HOME/.mindivy/mcp_token" | tr -d '[:space:]')"
fi
if [ -z "$MCP_TOKEN" ]; then
  echo "mindivy-mcp: no MCP token. Run the Mindivy app once (Settings → External Agent Access), or set MCP_TOKEN." >&2
  exit 1
fi

export MCP_TOKEN
export MINDIVY_BACKEND_URL="${MINDIVY_BACKEND_URL:-http://127.0.0.1:8000}"
if [ -n "$PYTHONPATH" ]; then
  export PYTHONPATH
fi

exec "$PYTHON" -m mindivy_mcp
