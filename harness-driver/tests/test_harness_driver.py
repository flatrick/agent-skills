import importlib.util
import json
import os
import stat
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "harness_driver.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harness_driver", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fake_omp(directory: Path, behavior: str) -> Path:
    executable = directory / "omp"
    source = """#!/usr/bin/env python3
import json
import sys
import time

if "--version" in sys.argv:
    print("omp/18.1.21")
    raise SystemExit(0)

""" + textwrap.dedent(behavior).strip() + "\n"
    executable.write_text(source, encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


class HarnessDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def request(self, cwd: Path, **overrides):
        values = {
            "harness": "omp",
            "prompt": "Reply with exactly OK.",
            "timeout_seconds": 2,
            "child_cwd": cwd,
            "model": None,
        }
        values.update(overrides)
        return self.module.HarnessRequest(**values)

    def test_build_omp_command_isolates_the_prompt(self):
        request = self.request(Path("/tmp/probe-cwd"), model="local/model")

        command = self.module.build_omp_command(request, "/usr/bin/omp")

        self.assertEqual(command[0], "/usr/bin/omp")
        for flag in (
            "-p",
            "--mode=json",
            "--no-tools",
            "--no-session",
            "--no-extensions",
            "--no-skills",
            "--no-rules",
            "--system-prompt=Follow the user message. Answer the task directly.",
        ):
            self.assertEqual(command.count(flag), 1)
        self.assertEqual(command[-2:], ["--model=local/model", "Reply with exactly OK."])
        self.assertIn("--cwd=/tmp/probe-cwd", command)
        self.assertNotIn("--approval-mode=write", command)
        self.assertNotIn("--auto-approve", command)

    def test_parse_omp_jsonl_returns_last_complete_reply(self):
        first = {
            "type": "turn_end",
            "message": {
                "role": "assistant",
                "provider": "llama-cpp",
                "model": "old-model",
                "content": [{"type": "text", "text": "old"}],
            },
            "toolResults": [],
        }
        final = {
            "type": "turn_end",
            "message": {
                "role": "assistant",
                "provider": "llama-cpp",
                "model": "Qwen3.6-35B-A3B-IQ4-coder",
                "stopReason": "stop",
                "content": [
                    {"type": "thinking", "thinking": "ignore me"},
                    {"type": "text", "text": "O"},
                    {"type": "text", "text": "K"},
                ],
            },
            "toolResults": [],
        }
        terminal = {"type": "agent_end", "isTerminal": True}
        stream = "progress\n" + "\n".join(json.dumps(item) for item in (first, final, terminal))

        reply = self.module.parse_omp_jsonl(stream)

        self.assertEqual(reply.text, "OK")
        self.assertEqual(reply.provider, "llama-cpp")
        self.assertEqual(reply.model, "Qwen3.6-35B-A3B-IQ4-coder")
        self.assertEqual(reply.stop_reason, "stop")

    def test_parse_omp_jsonl_rejects_incomplete_or_malformed_streams(self):
        with self.assertRaisesRegex(ValueError, "terminal agent_end"):
            self.module.parse_omp_jsonl(
                json.dumps(
                    {
                        "type": "turn_end",
                        "message": {"role": "assistant", "content": [{"type": "text", "text": "OK"}]},
                        "toolResults": [],
                    }
                )
            )
        with self.assertRaisesRegex(ValueError, "malformed JSON"):
            self.module.parse_omp_jsonl('{"type":"turn_end"')

    def test_run_harness_preserves_timeout_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_fake_omp(
                root,
                "print(json.dumps({'type': 'session'}), flush=True)\n"
                "print('startup warning', file=sys.stderr, flush=True)\n"
                "time.sleep(5)",
            )
            with mock.patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ["PATH"]}):
                result = self.module.run_harness(self.request(root, timeout_seconds=1))

        self.assertEqual(result.status, self.module.RunStatus.TIMED_OUT)
        self.assertIsNone(result.exit_code)
        self.assertIn('"type": "session"', result.stdout)
        self.assertEqual(result.stderr.strip(), "startup warning")

    def test_run_harness_distinguishes_child_and_protocol_failures(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_fake_omp(root, "print('denied', file=sys.stderr)\nraise SystemExit(7)")
            with mock.patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ["PATH"]}):
                child_failure = self.module.run_harness(self.request(root))

            write_fake_omp(root, "print(json.dumps({'type': 'session'}))")
            with mock.patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ["PATH"]}):
                protocol_failure = self.module.run_harness(self.request(root))

        self.assertEqual(child_failure.status, self.module.RunStatus.CHILD_FAILED)
        self.assertEqual(child_failure.exit_code, 7)
        self.assertEqual(child_failure.stderr.strip(), "denied")
        self.assertEqual(protocol_failure.status, self.module.RunStatus.INVALID_OUTPUT)
        self.assertIn("turn_end", protocol_failure.error)

    def test_run_harness_extracts_observed_identity_and_closes_stdin(self):
        behavior = """
        if sys.stdin.read() != '':
            raise SystemExit(9)
        message = {
            'role': 'assistant',
            'provider': 'llama-cpp',
            'model': 'Qwen3.6-35B-A3B-IQ4-coder',
            'stopReason': 'stop',
            'content': [{'type': 'text', 'text': 'OK'}],
        }
        print(json.dumps({'type': 'turn_end', 'message': message, 'toolResults': []}))
        print(json.dumps({'type': 'agent_end', 'isTerminal': True}))
        """
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_fake_omp(root, behavior)
            with mock.patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ["PATH"]}):
                result = self.module.run_harness(self.request(root))

        self.assertEqual(result.status, self.module.RunStatus.COMPLETED)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.harness_version, "omp/18.1.21")
        self.assertEqual(result.assistant.text, "OK")
        self.assertEqual(result.assistant.provider, "llama-cpp")


if __name__ == "__main__":
    unittest.main()
