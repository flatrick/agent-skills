import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "codex_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_review", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def jsonl(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


class BuildCommandTests(unittest.TestCase):
    def test_sandbox_is_read_only_and_prompt_comes_from_stdin(self):
        review = load_module()
        request = review.ReviewRequest(Path("C:/repo"), "p", 60, model="gpt-x")

        with mock.patch.object(review.sys, "platform", "linux"):
            command = review.build_command(request, "codex")

        self.assertEqual(
            [
                "codex", "exec", "--json", "--ephemeral", "--ignore-user-config",
                "--skip-git-repo-check", "-s", "read-only", "-C", str(Path("C:/repo")),
                "-m", "gpt-x", "-",
            ],
            command,
        )

    def test_windows_selects_the_sandbox_the_ignored_user_config_would_have(self):
        review = load_module()
        request = review.ReviewRequest(Path("C:/repo"), "p", 60)

        with mock.patch.object(review.sys, "platform", "win32"):
            command = review.build_command(request, "codex")

        self.assertEqual(
            [
                "codex", "exec", "--json", "--ephemeral", "--ignore-user-config",
                "-c", 'windows.sandbox="elevated"',
                "--skip-git-repo-check", "-s", "read-only", "-C", str(Path("C:/repo")), "-",
            ],
            command,
        )


class FinalAnswerTests(unittest.TestCase):
    def test_returns_last_agent_message_and_accepts_tool_use(self):
        review = load_module()
        output = jsonl(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "reading"}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": "git diff"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Nothing found."}},
            {"type": "turn.completed"},
        )

        self.assertEqual("Nothing found.", review.final_answer(output))

    def test_failed_turn_is_an_error(self):
        review = load_module()
        output = jsonl({"type": "turn.failed", "error": {"message": "quota"}})

        with self.assertRaisesRegex(ValueError, "quota"):
            review.final_answer(output)

    def test_completed_turn_followed_by_an_unfinished_turn_is_an_error(self):
        review = load_module()
        output = jsonl(
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "first"}},
            {"type": "turn.completed"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "partial"}},
        )

        with self.assertRaisesRegex(ValueError, "no turn.completed"):
            review.final_answer(output)

    def test_item_after_turn_completed_without_a_new_turn_is_an_error(self):
        review = load_module()
        output = jsonl(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
            {"type": "turn.completed"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "stray"}},
        )

        with self.assertRaisesRegex(ValueError, "after turn.completed"):
            review.final_answer(output)

    def test_only_completed_agent_messages_count(self):
        review = load_module()
        output = jsonl(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "final"}},
            {"type": "item.started", "item": {"type": "agent_message", "text": "draft"}},
            {"type": "turn.completed"},
        )

        self.assertEqual("final", review.final_answer(output))

    def test_incomplete_turn_is_an_error(self):
        review = load_module()
        output = jsonl({"type": "item.completed", "item": {"type": "agent_message", "text": "half"}})

        with self.assertRaisesRegex(ValueError, "no turn.completed"):
            review.final_answer(output)


class EvidenceRootTests(unittest.TestCase):
    def git(self, cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    def test_linked_worktree_writes_under_main_checkout_scratch(self):
        review = load_module()
        with tempfile.TemporaryDirectory() as temp:
            main = Path(temp) / "main"
            main.mkdir()
            self.git(main, "init", "-q")
            self.git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "root")
            linked = main / ".worktrees" / "feature"
            self.git(main, "worktree", "add", "-q", "-b", "feature", str(linked))

            self.assertEqual(
                main.resolve() / ".scratch" / "feature" / "codex",
                review.default_evidence_root(linked),
            )
            self.assertEqual(main.resolve() / ".scratch" / "codex", review.default_evidence_root(main))


class TimeoutTests(unittest.TestCase):
    SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]

    def request(self, review, temp):
        return review.ReviewRequest(Path(temp), "prompt", timeout_seconds=1)

    def test_timeout_stops_the_child_and_reports_timed_out(self):
        review = load_module()
        review.build_command = lambda request, executable: self.SLEEPER
        with tempfile.TemporaryDirectory() as temp:
            result = review.run_review(self.request(review, temp), "unused")

        self.assertEqual(review.RunStatus.TIMED_OUT, result.status)
        self.assertEqual("timed out after 1s", result.error)

    def test_timeout_reports_timed_out_when_termination_fails(self):
        review = load_module()
        review.build_command = lambda request, executable: self.SLEEPER
        started = []

        def failing_stop(process):
            started.append(process)
            raise OSError("no such process group")

        review._stop_process = failing_stop
        review._kill_process = failing_stop
        with tempfile.TemporaryDirectory() as temp:
            try:
                result = review.run_review(self.request(review, temp), "unused")
            finally:
                for process in started[:1]:
                    process.kill()
                    process.communicate(timeout=10)

        self.assertEqual(review.RunStatus.TIMED_OUT, result.status)
        self.assertEqual(2, len(started))


class MainTests(unittest.TestCase):
    def test_missing_prompt_file_fails_before_running_codex(self):
        review = load_module()
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "evidence"

            code = review.main(["--prompt-file", str(Path(temp) / "absent.txt"), "--worktree", temp, "--out", str(out)])

            self.assertEqual(2, code)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
