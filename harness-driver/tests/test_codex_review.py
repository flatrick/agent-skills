import importlib.util
import json
import platform
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


class PythonNoteTests(unittest.TestCase):
    NOTE = "Run & 'C:\\Py & 3\\python.exe' -B\n"
    # CRLF, a lone CR and non-ASCII text must reach Codex exactly as the file holds them.
    PROMPT = "Line one\r\nLine two\rcafé\n"

    def test_note_precedes_the_prompt_which_arrives_unchanged(self):
        review = load_module()
        request = review.ReviewRequest(Path("C:/repo"), self.PROMPT, 60, note=self.NOTE)

        stdin = review.review_stdin(request)

        self.assertIn(self.NOTE, stdin)
        self.assertTrue(stdin.endswith(self.PROMPT))
        self.assertLess(stdin.index(self.NOTE), stdin.index(self.PROMPT))

    def test_without_a_note_stdin_is_the_prompt(self):
        review = load_module()

        self.assertEqual(self.PROMPT, review.review_stdin(review.ReviewRequest(Path("C:/repo"), self.PROMPT, 60)))

    def test_note_never_travels_as_an_argument(self):
        review = load_module()
        request = review.ReviewRequest(Path("C:/repo"), self.PROMPT, 60, note=self.NOTE)

        with mock.patch.object(review.sys, "platform", "win32"):
            command = review.build_command(request, "codex")

        # cmd.exe reparses the codex.cmd shim's arguments and splits them at "&".
        self.assertFalse([arg for arg in command if "python.exe" in arg or "developer_instructions" in arg])

    def test_codex_receives_the_note_and_prompt_on_stdin(self):
        review = load_module()
        echo = (
            "import json, sys\n"
            "text = sys.stdin.buffer.read().decode('utf-8')\n"
            "print(json.dumps({'type': 'turn.started'}))\n"
            "print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': text}}))\n"
            "print(json.dumps({'type': 'turn.completed', 'usage': {}}))\n"
        )
        review.build_command = lambda request, executable: [sys.executable, "-c", echo]
        with tempfile.TemporaryDirectory() as temp:
            request = review.ReviewRequest(Path(temp), self.PROMPT, 60, note=self.NOTE)

            result = review.run_review(request, "unused")

        self.assertEqual(review.RunStatus.COMPLETED, result.status)
        self.assertEqual(review.review_stdin(request), result.answer)

    def test_candidates_are_reduced_to_the_distinct_interpreters_they_run(self):
        review = load_module()
        answers = {
            "own": ("/opt/py/bin/python3", "3.14.3"),
            "alias": ("/opt/py/bin/python3", "3.14.3"),
            "broken": None,
            "other": ("/usr/bin/python3", "3.12.1"),
        }

        found = review.discover_pythons(["own", "alias", "broken", "other"], answers.get)

        self.assertEqual([("/opt/py/bin/python3", "3.14.3"), ("/usr/bin/python3", "3.12.1")], found)

    def test_probe_reports_the_real_interpreter_and_its_version(self):
        review = load_module()

        found = review.probe_python(sys.executable)

        self.assertEqual((sys.executable, platform.python_version()), found)

    def test_probe_of_a_missing_executable_finds_nothing(self):
        review = load_module()

        self.assertIsNone(review.probe_python(str(Path(tempfile.gettempdir()) / "no-such-python")))

    def test_windows_note_names_each_interpreter_and_the_powershell_call(self):
        review = load_module()

        with mock.patch.object(review.sys, "platform", "win32"):
            note = review.python_note([("C:\\Py\\python.exe", "3.14.3")])

        self.assertIn("C:\\Py\\python.exe (Python 3.14.3)", note)
        self.assertIn("& 'C:\\Py\\python.exe' -B", note)

    def test_posix_note_runs_the_interpreter_by_path(self):
        review = load_module()

        with mock.patch.object(review.sys, "platform", "linux"):
            note = review.python_note([("/usr/bin/python3", "3.12.1")])

        self.assertIn("/usr/bin/python3 (Python 3.12.1)", note)
        self.assertIn("'/usr/bin/python3' -B", note)
        self.assertNotIn("&", note)

    def test_no_interpreter_means_no_note(self):
        review = load_module()

        self.assertIsNone(review.python_note([]))

    def test_evidence_records_exactly_what_codex_received(self):
        review = load_module()
        result = review.ReviewResult(review.RunStatus.COMPLETED, 0, 1, "ok", "", "", None)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "evidence"

            review.write_evidence(out, self.PROMPT, Path(temp), result, stdin=self.NOTE + self.PROMPT)

            self.assertEqual(self.PROMPT.encode("utf-8"), (out / "prompt.txt").read_bytes())
            self.assertEqual((self.NOTE + self.PROMPT).encode("utf-8"), (out / "stdin.txt").read_bytes())


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
