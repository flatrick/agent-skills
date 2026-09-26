import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "codex_worker.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_worker", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FAKE_CODEX_EVENTS = "\n".join(
    json.dumps(event)
    for event in [
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Wrote hello.txt."}},
        {"type": "turn.completed"},
    ]
)


def fake_codex(extra=""):
    script = (
        "import pathlib, sys\n"
        "sys.stdin.read()\n"
        "pathlib.Path('hello.txt').write_text('hello from the worker\\n')\n"
        + extra
        + "print({!r})\n".format(FAKE_CODEX_EVENTS)
    )
    return [sys.executable, "-c", script]


class BuildCommandTests(unittest.TestCase):
    def test_sandbox_is_danger_full_access_and_prompt_comes_from_stdin(self):
        worker = load_module()
        request = worker.WorkerRequest(Path("C:/wt"), "p", 60, model="gpt-x", project_docs=False)

        command = worker.build_command(request, "codex")

        self.assertEqual(
            [
                "codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check",
                "-s", "danger-full-access", "-C", str(Path("C:/wt")),
                "-c", "project_doc_max_bytes=0", "-m", "gpt-x", "-",
            ],
            command,
        )


class MainTests(unittest.TestCase):
    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, encoding="utf-8").stdout

    def make_repo(self, temp):
        repo = Path(temp) / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        (repo / ".gitignore").write_text(".worktrees/\n.scratch/\n")
        self.git(repo, "add", ".gitignore")
        self.git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "root")
        prompt = Path(temp) / "prompt.txt"
        prompt.write_text("write hello.txt\n")
        return repo, prompt

    def test_refuses_without_unsandboxed_and_creates_no_worktree(self):
        worker = load_module()
        with tempfile.TemporaryDirectory() as temp:
            repo, prompt = self.make_repo(temp)

            code = worker.main(["--prompt-file", str(prompt), "--repo", str(repo)])

            self.assertEqual(2, code)
            self.assertFalse((repo / ".worktrees").exists())
            self.assertEqual(1, self.git(repo, "worktree", "list", "--porcelain").count("worktree "))

    def test_worker_diff_is_collected_from_a_throwaway_worktree(self):
        worker = load_module()
        worker.build_command = lambda request, executable: fake_codex()
        with tempfile.TemporaryDirectory() as temp:
            repo, prompt = self.make_repo(temp)
            out = Path(temp) / "evidence"

            with mock.patch.object(worker.shutil, "which", return_value="codex"):
                code = worker.main(["--prompt-file", str(prompt), "--repo", str(repo), "--label", "t", "--out", str(out), "--unsandboxed"])

            record = json.loads((out / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(0, code)
            self.assertEqual("completed", record["status"])
            self.assertEqual(["hello.txt"], record["changed_files"])
            self.assertEqual([], record["warnings"])
            self.assertEqual((repo / ".worktrees").resolve(), Path(record["worktree"]).parent)
            self.assertIn("+hello from the worker", (out / "patch.diff").read_text(encoding="utf-8"))
            self.assertEqual("Wrote hello.txt.\n", (out / "answer.txt").read_text(encoding="utf-8"))
            self.assertFalse((repo / "hello.txt").exists())

    def test_write_to_the_supervising_worktree_is_a_warning(self):
        worker = load_module()
        with tempfile.TemporaryDirectory() as temp:
            repo, prompt = self.make_repo(temp)
            escape = "pathlib.Path({!r}).write_text('escaped\\n')\n".format(str(repo / "escaped.txt"))
            worker.build_command = lambda request, executable: fake_codex(escape)
            out = Path(temp) / "evidence"

            with mock.patch.object(worker.shutil, "which", return_value="codex"):
                code = worker.main(["--prompt-file", str(prompt), "--repo", str(repo), "--out", str(out), "--unsandboxed"])

            record = json.loads((out / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(1, code)
            self.assertEqual("completed", record["status"])
            self.assertEqual(1, len(record["warnings"]))

    def run_main(self, worker, temp, extra, prepare=None):
        repo, prompt = self.make_repo(temp)
        if prepare:
            prepare(repo)
        worker.build_command = lambda request, executable: fake_codex(extra(repo) if callable(extra) else extra)
        out = Path(temp) / "evidence"
        with mock.patch.object(worker.shutil, "which", return_value="codex"):
            code = worker.main(["--prompt-file", str(prompt), "--repo", str(repo), "--out", str(out), "--unsandboxed"])
        return code, out, json.loads((out / "result.json").read_text(encoding="utf-8"))

    def test_second_write_to_an_already_dirty_file_is_a_warning(self):
        worker = load_module()

        def dirty(repo):
            (repo / ".gitignore").write_text(".worktrees/\n.scratch/\n# dirty\n")

        def append(repo):
            return "open({!r}, 'a').write('# again\\n')\n".format(str(repo / ".gitignore"))

        with tempfile.TemporaryDirectory() as temp:
            code, _, record = self.run_main(worker, temp, append, dirty)

        self.assertEqual(1, code)
        self.assertEqual(1, len(record["warnings"]))

    def test_write_under_an_ignored_directory_of_the_supervising_worktree_is_a_warning(self):
        worker = load_module()

        def scratch(repo):
            (repo / ".scratch").mkdir()
            (repo / ".scratch" / "old.log").write_text("old\n")

        def write(repo):
            return "pathlib.Path({!r}).write_text('new\\n')\n".format(str(repo / ".scratch" / "new.log"))

        with tempfile.TemporaryDirectory() as temp:
            code, _, record = self.run_main(worker, temp, write, scratch)

        self.assertEqual(1, code)
        self.assertEqual(1, len(record["warnings"]))

    def test_ignored_files_the_worker_created_are_listed(self):
        worker = load_module()
        extra = "pathlib.Path('.scratch').mkdir(); pathlib.Path('.scratch/build.log').write_text('x\\n')\n"
        with tempfile.TemporaryDirectory() as temp:
            code, out, record = self.run_main(worker, temp, extra)

            self.assertEqual(0, code)
            self.assertEqual(1, record["ignored_files"])
            self.assertEqual(".scratch/build.log\n", (out / "ignored.txt").read_text(encoding="utf-8"))

    def test_patch_keeps_crlf_and_non_utf8_bytes(self):
        worker = load_module()
        extra = (
            "pathlib.Path('.gitattributes').write_bytes(b'*.bin -text\\n')\n"
            "pathlib.Path('crlf.bin').write_bytes(b'a\\r\\n')\n"
            "pathlib.Path('latin1.txt').write_bytes(b'caf\\xe9\\n')\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            code, out, _ = self.run_main(worker, temp, extra)

            patch = (out / "patch.diff").read_bytes()
        self.assertEqual(0, code)
        self.assertIn(b"+caf\xe9\n", patch)
        self.assertIn(b"+a\r\n", patch)

    def test_git_failure_after_the_run_still_writes_evidence(self):
        worker = load_module()
        extra = "pathlib.Path('.git').unlink()\n"
        with tempfile.TemporaryDirectory() as temp:
            code, out, record = self.run_main(worker, temp, extra)

            self.assertEqual(1, code)
            self.assertEqual("completed", record["status"])
            self.assertIsNotNone(record["collection_error"])
            self.assertTrue((out / "answer.txt").exists())


if __name__ == "__main__":
    unittest.main()
