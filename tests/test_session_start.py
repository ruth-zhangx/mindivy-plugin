"""Regression tests for the SessionStart task-count hook (G314 / T304).

Run from the repo root:

    python3 -m unittest discover -s tests -v
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "mindivy"
    / "hooks"
    / "session_start.py"
)


def load_hook():
    spec = importlib.util.spec_from_file_location("mindivy_session_start", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CountOpenTasksTest(unittest.TestCase):
    def setUp(self):
        self.hook = load_hook()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.inventory = Path(self.tmp.name) / "master-task-inventory.md"

    def write_inventory(self, lines):
        self.inventory.write_text("\n".join(lines), encoding="utf-8")

    def test_mixed_bold_and_plain_rows_are_both_counted(self):
        # Fixture mirrors the real inventory's row shape: leading/trailing
        # pipes, status in the 4th split cell, plain and bold task IDs mixed.
        self.write_inventory(
            [
                "| 标记 | 含义 |",
                "|------|------|",
                "| `[ ]` | 未开始 |",
                "| T014 | plain open task | `[ ]` 2026-06-22 |",
                "| **T274** | bold in-progress task | `[~]` 2026-09-12 |",
                "| **T303** | bold Ruth-blocked task | `[R]` 2026-10-23 |",
                "| **T179** | bold deferred task | `[D]` 2026-09-20 |",
            ]
        )
        self.assertEqual(
            self.hook.count_open_tasks(self.inventory),
            {"open": 1, "in_progress": 1, "blocked": 1},
        )

    def test_non_task_rows_are_not_counted(self):
        # The legend and the demand-signal table carry the same markers but
        # are 2- and 4-column tables, not task rows.
        self.write_inventory(
            [
                "| 标记 | 含义 |",
                "|------|------|",
                "| `[ ]` | 未开始 |",
                "| `[~]` | 进行中 / 部分完成 |",
                "| T041-voice | 英语单词 TTS 语音朗读 | T041 延后 | 用户反馈需要 |",
                "Prose mentioning T304 `[ ]` is not a table row.",
            ]
        )
        self.assertEqual(
            self.hook.count_open_tasks(self.inventory),
            {"open": 0, "in_progress": 0, "blocked": 0},
        )

    def test_missing_inventory_returns_none(self):
        missing = Path(self.tmp.name) / "does-not-exist.md"
        self.assertIsNone(self.hook.count_open_tasks(missing))

    def test_digest_reports_counts_for_bold_task_rows(self):
        # End-to-end: the user-visible digest line must reflect bold IDs.
        repo = Path(self.tmp.name) / "repo"
        (repo / "docs" / "checkpoints").mkdir(parents=True)
        (repo / "docs" / "assets").mkdir()
        (repo / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
        (repo / "docs" / "checkpoints" / "20260101-000000-fixture.md").write_text(
            "---\ntimestamp: 2026-01-01T00:00:00+08:00\n---\n\n"
            "## Working on: fixture\n\n### Remaining Work\n\n1. item\n",
            encoding="utf-8",
        )
        (repo / "docs" / "assets" / "master-task-inventory.md").write_text(
            "\n".join(
                [
                    "| T014 | plain open task | `[ ]` 2026-06-22 |",
                    "| **T274** | bold in-progress task | `[~]` 2026-09-12 |",
                ]
            ),
            encoding="utf-8",
        )
        digest = self.hook.build_digest(str(repo), {})
        self.assertIn("- Task inventory: 1 open, 1 in progress, 0 blocked", digest)


if __name__ == "__main__":
    unittest.main()
