# ---
# @status: active
# @kind: Hook
# @input: stdin JSON (Claude Code SessionStart payload: {session_id, transcript_path, cwd, permission_mode, hook_event_name, source})
# @output: stdout JSON {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<digest>"}} (only when a digest was built)
# @side_effects: none
# @description: T186 plugin SessionStart hook — inject Mindivy workspace state (latest checkpoint + open tasks) via additionalContext. H10 pattern: stdlib-only, never raises, always exit 0. Binds to the cwd from stdin payload, never the process CWD (G076/G077). Digest starts with a wall-clock "Now" line (G128).
# ---

"""Mindivy workspace-state digest for Claude Code SessionStart.

Resolution order (first hit wins):
1. `$MINDIVY_REPO` env — explicit repo path (exists + is a dir).
2. Walk up from the session cwd looking for `docs/checkpoints/` + `CLAUDE.md`.
3. `<app-data-dir>/workspace-state.md` — app-written digest (passive reader;
   written by python-service/core/workspace_state.py, T192). The dir is
   resolved per platform (T021): MINDIVY_DATA_DIR env > %APPDATA%/.mindivy
   (win32) > ~/Library/Application Support/.mindivy (darwin) > ~/.mindivy.
4. Nothing found → silent no-op, exit 0.

Digest sources (dev mode): newest checkpoint frontmatter + Remaining Work list
(`docs/checkpoints/*.md`, YYYYMMDD-HHMMSS filename prefix sorts lexicographically)
and open-task counts from `docs/assets/master-task-inventory.md`
(`| T<digits> |` and `| **T<digits>** |` rows — the 2-column legend table
carries the same markers and must be excluded). Digest line 2 is a wall-clock
`Now` stamp (G128) — the checkpoint timestamp is a stale snapshot, never a
substitute for real time.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

MAX_REMAINING_ITEMS = 5
MAX_ITEM_CHARS = 100
MAX_STATE_FILE_LINES = 40

_TITLE_RE = re.compile(r"^##\s+Working on:\s*(.+)$")
_DATE_RE = re.compile(r"^timestamp:\s*(.+)$")
_SECTION_RE = re.compile(r"^###\s+")
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_TASK_ROW_RE = re.compile(r"^\|\s*\*{0,2}T\d+\*{0,2}\s*\|")


def find_repo(cwd: str) -> "Path | None":
    """Walk up from cwd to the filesystem root looking for the Mindivy repo
    (anchors: `docs/checkpoints/` dir + `CLAUDE.md`). Returns None on any error."""
    try:
        start = Path(cwd)
        if not start.is_absolute():
            return None
        for parent in [start] + list(start.parents):
            if (parent / "docs" / "checkpoints").is_dir() and (parent / "CLAUDE.md").is_file():
                return parent
    except (OSError, ValueError):
        return None
    return None


def newest_checkpoint(checkpoints_dir: "Path") -> "Path | None":
    """Newest checkpoint by filename (YYYYMMDD-HHMMSS-... sorts lexicographically);
    mtime as tiebreak for hand-renamed files. Skips hidden files and non-.md."""
    try:
        candidates = [
            p
            for p in checkpoints_dir.iterdir()
            if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda p: (p.name, p.stat().st_mtime))
    except OSError:
        return None


def parse_checkpoint(path: "Path") -> dict:
    """Extract {title, date, remaining} from a checkpoint file. Malformed
    frontmatter/sections degrade gracefully — keep what parsed."""
    title, date = None, None
    remaining: list[str] = []
    in_remaining = False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"title": None, "date": None, "remaining": []}

    for line in text.splitlines():
        m = _TITLE_RE.match(line)
        if m and title is None:
            title = m.group(1).strip()
            continue
        m = _DATE_RE.match(line)
        if m and date is None:
            date = m.group(1).strip()[:10]  # 2026-08-14T13:52:00+08:00 → date part
            continue
        if line.startswith("### "):
            in_remaining = line.strip() == "### Remaining Work"
            continue
        if in_remaining:
            m = _NUMBERED_RE.match(line)
            if m:
                item = m.group(2).strip()
                if len(item) > MAX_ITEM_CHARS:
                    item = item[: MAX_ITEM_CHARS - 1].rstrip() + "…"
                remaining.append(f"{m.group(1)}. {item}")
                if len(remaining) >= MAX_REMAINING_ITEMS:
                    break

    if date is None:
        date = path.name.split("-")[0]  # fallback: filename date prefix (YYYYMMDD)
    return {"title": title, "date": date, "remaining": remaining}


def count_open_tasks(inventory: "Path") -> "dict | None":
    """Count open task rows in master-task-inventory.md. Only rows starting
    with `| T<digits> |` or `| **T<digits>** |` are task rows — the 2-column
    legend table uses the same markers and must be excluded. Status sits in
    the 4th split cell (backticked: `[ ]` / `[~]` / `[R]`). Returns None when
    the inventory is missing/unreadable (caller omits the line, never reports
    false zeros)."""
    counts = {"open": 0, "in_progress": 0, "blocked": 0}
    try:
        text = inventory.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if not _TASK_ROW_RE.match(line):
            continue
        cells = line.split("|")
        if len(cells) < 5:
            continue
        status = cells[3]  # cells[0]='' cells[1]=T<id> cells[2]=subject cells[3]=status
        if "`[ ]`" in status:
            counts["open"] += 1
        elif "`[~]`" in status:
            counts["in_progress"] += 1
        elif "`[R]`" in status:
            counts["blocked"] += 1
    return counts


def resolve_app_data_dir(env: dict) -> "Path":
    """Platform data dir — mirrors python-service/core/app_paths.py (T021).
    The app writes the digest inside its data dir; this hook must read the
    same location on every platform (E25 single shared state path).
    Priority: MINDIVY_DATA_DIR env > win32 %APPDATA%/.mindivy > darwin
    ~/Library/Application Support/.mindivy > ~/.mindivy. Hermetic: uses the
    passed env dict (never os.environ), so tests can redirect HOME."""
    override = (env.get("MINDIVY_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    home = Path(env.get("HOME") or "~").expanduser()
    if sys.platform == "win32":
        appdata = (env.get("APPDATA") or "").strip()
        if appdata:
            return Path(appdata) / ".mindivy"
        return home / ".mindivy"
    if sys.platform == "darwin":
        return home / "Library/Application Support/.mindivy"
    return home / ".mindivy"


def load_workspace_state(env: dict) -> "str | None":
    """Passive reader for the app-written digest file (T192:
    python-service/core/workspace_state.py writes it — startup/unlock force
    refresh, write-request throttle, empty on lock). Reads verbatim,
    truncated to MAX_STATE_FILE_LINES."""
    state_file = resolve_app_data_dir(env) / "workspace-state.md"
    try:
        if not state_file.is_file():
            return None
        lines = state_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return "\n".join(lines[:MAX_STATE_FILE_LINES]).strip() or None


def build_digest(cwd: "str | None", env: dict) -> str:
    """Build the compact workspace digest. Returns "" when nothing found."""
    repo = None
    repo_env = env.get("MINDIVY_REPO", "").strip()
    if repo_env:
        candidate = Path(repo_env).expanduser()
        if candidate.is_dir():
            repo = candidate
    if repo is None and cwd:
        repo = find_repo(cwd)

    if repo is not None:
        checkpoint = newest_checkpoint(repo / "docs" / "checkpoints")
        info = parse_checkpoint(checkpoint) if checkpoint else None
        counts = count_open_tasks(repo / "docs" / "assets" / "master-task-inventory.md")
        lines = [
            f"**Mindivy workspace state** (auto-injected by the mindivy plugin — repo: {repo})",
            f"- **Now: {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}**",
        ]
        if info and (info["title"] or info["remaining"]):
            cp_name = checkpoint.name
            title_part = f' — "{info["title"]}"' if info["title"] else ""
            lines.append(
                f"- Latest checkpoint: `{cp_name}`{title_part} ({info['date']})"
            )
            for item in info["remaining"]:
                lines.append(f"  - {item}")
        if counts is not None:
            lines.append(
                f"- Task inventory: {counts['open']} open, {counts['in_progress']} in progress,"
                f" {counts['blocked']} blocked"
            )
        lines.append(
            "- Co-creation: `/mindivy:research` grounds you in the knowledge base; "
            "`/mindivy:draft-chapter` co-writes chapters. The `mindivy` skill covers "
            "retrieval and citation rules — follow it before writing anything "
            "grounded in saved knowledge."
        )
        return "\n".join(lines)

    state = load_workspace_state(env)
    if state:
        state_dir = resolve_app_data_dir(env)
        return (
            f"**Mindivy workspace state** (from {state_dir}/workspace-state.md)\n" + state
        )
    return ""


def main() -> None:
    """Never raises, always exits 0 (E16). Outputs the hook JSON wrapper only
    when a digest was built."""
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()
        if not raw:
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return
        cwd = payload.get("cwd")
        if not isinstance(cwd, str):
            cwd = None
        digest = build_digest(cwd, dict(os.environ))
        if not digest:
            return
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": digest,
                    }
                },
                ensure_ascii=False,
            )
        )
    except Exception:
        pass  # hooks must never block the session (E16)


if __name__ == "__main__":
    main()
