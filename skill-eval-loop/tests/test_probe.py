import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "probe.py"


def load_probe_module():
    spec = importlib.util.spec_from_file_location("probe_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fake_omp(directory: Path, exit_code: int = 0) -> Path:
    executable = directory / "omp"
    source = f"""#!/usr/bin/env python3
import json
import sys

if "--version" in sys.argv:
    print("omp/18.1.21")
    raise SystemExit(0)

if {exit_code}:
    print("child failed", file=sys.stderr)
    raise SystemExit({exit_code})

message = {{
    "role": "assistant",
    "provider": "llama-cpp",
    "model": "fake-model",
    "stopReason": "stop",
    "content": [{{"type": "text", "text": "OK"}}],
}}
print(json.dumps({{"type": "turn_end", "message": message, "toolResults": []}}))
print(json.dumps({{"type": "agent_end", "isTerminal": True}}))
"""
    executable.write_text(source, encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


class ProbeCliTests(unittest.TestCase):
    def run_probe(self, cwd: Path, fake_bin: Path, out: Path, *extra: str):
        env = dict(os.environ)
        env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--task",
                "Reply with exactly OK.",
                "--runs",
                "2",
                "--out",
                str(out),
                *extra,
            ],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_cli_runs_from_unrelated_directory_and_writes_structured_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            write_fake_omp(fake_bin)
            unrelated = root / "unrelated"
            unrelated.mkdir()
            out = root / "runs" / "00-baseline"

            completed = self.run_probe(unrelated, fake_bin, out)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["runs_requested"], 2)
            self.assertEqual(manifest["completed"], 2)
            self.assertEqual(manifest["failed"], 0)
            self.assertEqual(manifest["harness_version"], "omp/18.1.21")
            self.assertEqual(len(manifest["prompt_sha256"]), 64)
            self.assertEqual((out / "run-001" / "answer.txt").read_text(encoding="utf-8"), "OK\n")
            first = json.loads((out / "run-001" / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(first["status"], "completed")
            self.assertEqual(first["assistant"]["model"], "fake-model")
            request = json.loads((out / "request.json").read_text(encoding="utf-8"))
            self.assertIn("harness_driver.py", request["command_template"][1])
            self.assertIn("--prompt-file", request["command_template"])

    def test_cli_refuses_to_overwrite_an_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "existing" / "keep.txt"
            marker.parent.mkdir()
            marker.write_text("unchanged", encoding="utf-8")

            completed = self.run_probe(root, fake_bin, marker.parent)

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "unchanged")

    def test_cli_returns_failure_when_any_child_fails_and_keeps_diagnostics(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            write_fake_omp(fake_bin, exit_code=7)
            out = root / "runs"

            completed = self.run_probe(root, fake_bin, out)

            self.assertEqual(completed.returncode, 1)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["completed"], 0)
            self.assertEqual(manifest["failed"], 2)
            first = json.loads((out / "run-001" / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(first["status"], "child_failed")
            self.assertEqual(first["exit_code"], 7)
            self.assertEqual((out / "run-001" / "stderr.txt").read_text(encoding="utf-8").strip(), "child failed")

    def test_missing_harness_driver_script_fails_cleanly(self):
        module = load_probe_module()
        module.HARNESS_DRIVER_SCRIPT = Path("/nonexistent/harness_driver.py")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out = root / "runs"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = module.main(["--task", "Reply with exactly OK.", "--runs", "1", "--out", str(out)])

        self.assertEqual(code, 2)
        self.assertIn("harness_driver.py", stderr.getvalue())
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
