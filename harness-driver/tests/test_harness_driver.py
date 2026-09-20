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
import threading
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "harness_driver.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harness_driver", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHIM_PREAMBLE = """import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

"""


def write_shim(directory: Path, name: str, behavior: str) -> Path:
    source = SHIM_PREAMBLE + textwrap.dedent(behavior).strip() + "\n"
    if os.name == "nt":
        implementation = directory / "{}_impl.py".format(name)
        implementation.write_text(source, encoding="utf-8")
        launcher = directory / "{}.cmd".format(name)
        launcher.write_text(
            '@echo off\r\n"{}" "{}" %*\r\n'.format(sys.executable, implementation),
            encoding="utf-8",
        )
    else:
        launcher = directory / name
        launcher.write_text("#!{}\n".format(sys.executable) + source, encoding="utf-8")
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
    return launcher


OMP_SHIM_PREFIX = """
if "--version" in sys.argv:
    print("omp/18.1.21")
    raise SystemExit(0)
"""


def write_fake_omp(directory: Path, behavior: str) -> Path:
    return write_shim(
        directory,
        "omp",
        OMP_SHIM_PREFIX.strip() + "\n" + textwrap.dedent(behavior).strip(),
    )


def write_sleeping_grandchild(directory: Path) -> Path:
    (directory / "sleeper.py").write_text(
        "import os\n"
        "import sys\n"
        "import time\n"
        "with open(sys.argv[1], 'a', encoding='utf-8') as handle:\n"
        "    print(os.getpid(), file=handle)\n"
        "time.sleep(120)\n",
        encoding="utf-8",
    )
    return directory / "descendant-pids.txt"


def reap(pidfile: Path) -> None:
    if not pidfile.exists():
        return
    for pid in pidfile.read_text(encoding="utf-8").split():
        subprocess.run(
            ["taskkill", "/PID", pid, "/T", "/F"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
        )


CODEX_SHIM_PREFIX = """
if "--version" in sys.argv:
    print("codex-cli 0.155.1")
    raise SystemExit(0)
RECORD = HERE / "codex-record"
(RECORD / "argv.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
(RECORD / "stdin.bin").write_bytes(sys.stdin.buffer.read())
"""


CODEX_COMPLETED_TURN = """
print(json.dumps({"type": "thread.started", "thread_id": "t1"}))
print(json.dumps({"type": "item.completed", "item": {
    "id": "item_0", "type": "error",
    "message": "Code Mode is unavailable because code-mode host is disabled."}}))
print(json.dumps({"type": "turn.started"}))
print(json.dumps({"type": "item.completed", "item": {
    "id": "item_1", "type": "reasoning", "text": "weighing the options"}}))
print(json.dumps({"type": "item.completed", "item": {
    "id": "item_2", "type": "agent_message", "text": "I'll answer that now."}}))
print(json.dumps({"type": "item.completed", "item": {
    "id": "item_3", "type": "agent_message", "text": "OK"}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 8451}}))
"""


def write_fake_codex(directory: Path, behavior: str) -> Path:
    record = directory / "codex-record"
    record.mkdir(exist_ok=True)
    write_shim(
        directory,
        "codex",
        CODEX_SHIM_PREFIX.strip() + "\n" + textwrap.dedent(behavior).strip(),
    )
    return record


def adjacent_pairs(command):
    return list(zip(command, command[1:]))


def codex_env(root: Path) -> dict:
    home = root / "codex-home"
    home.mkdir(exist_ok=True)
    return {
        "PATH": str(root) + os.pathsep + os.environ["PATH"],
        "CODEX_HOME": str(home),
    }


def run_with_deadline(call, seconds: float):
    box = {}

    def target():
        try:
            box["result"] = call()
        except BaseException as error:
            box["error"] = error

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(seconds)
    return worker.is_alive(), box


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
        expected_cwd = Path("/tmp/probe-cwd").resolve()
        self.assertIn("--cwd={}".format(expected_cwd), command)
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

    def test_parse_omp_jsonl_rejects_tool_results_from_any_turn(self):
        used_tools = {
            "type": "turn_end",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "used a tool"}]},
            "toolResults": [{"toolCallId": "t1"}],
        }
        clean = {
            "type": "turn_end",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "OK"}]},
            "toolResults": [],
        }
        terminal = {"type": "agent_end", "isTerminal": True}
        stream = "\n".join(json.dumps(item) for item in (used_tools, clean, terminal))

        with self.assertRaisesRegex(ValueError, "tool-free probe"):
            self.module.parse_omp_jsonl(stream)

    def test_parse_omp_jsonl_keeps_a_line_separator_inside_an_answer(self):
        turn = {
            "type": "turn_end",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "A\u2028B"}]},
            "toolResults": [],
        }
        terminal = {"type": "agent_end", "isTerminal": True}
        stream = "\n".join(json.dumps(item, ensure_ascii=False) for item in (turn, terminal))

        self.assertEqual(self.module.parse_omp_jsonl(stream).text, "A\u2028B")

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


class CodexCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def build(self, **overrides):
        values = {
            "harness": "codex",
            "prompt": "Reply with exactly OK.",
            "timeout_seconds": 30,
            "child_cwd": Path(tempfile.gettempdir()),
            "model": None,
        }
        values.update(overrides)
        return self.module.build_codex_command(
            self.module.HarnessRequest(**values), "/usr/bin/codex"
        )

    def test_codex_runs_the_model_in_a_read_only_sandbox(self):
        self.assertIn(("-s", "read-only"), adjacent_pairs(self.build()))

    def test_codex_keeps_no_session_state_between_runs(self):
        self.assertIn("--ephemeral", self.build())

    def test_codex_ignores_operator_config_that_would_skew_the_probe(self):
        self.assertIn("--ignore-user-config", self.build())

    def test_codex_disables_every_tool_surface_the_ablation_measured(self):
        measured = (
            ("-c", "project_doc_max_bytes=0"),
            ("-c", "skills.bundled.enabled=false"),
            ("-c", "web_search=disabled"),
            ("--disable", "apps"),
            ("--disable", "shell_tool"),
            ("--disable", "view_image"),
            ("--disable", "image_generation"),
            ("--disable", "sleep_tool"),
            ("--disable", "code_mode_host"),
        )
        pairs = adjacent_pairs(self.build())

        self.assertEqual(self.module.CODEX_ISOLATION_FLAGS, measured)
        for flag in measured:
            with self.subTest(flag=flag):
                self.assertIn(flag, pairs)

    def test_codex_takes_the_prompt_on_stdin_not_the_command_line(self):
        prompt = "first line\nsecond line with \"quotes\" and %TEMP%"

        command = self.build(prompt=prompt)

        self.assertEqual(command[-1], "-")
        self.assertNotIn(prompt, command)
        self.assertNotIn("first line", command)

    def test_codex_pins_the_model_only_when_one_is_requested(self):
        self.assertNotIn("-m", self.build())
        self.assertIn(("-m", "gpt-6-astra"), adjacent_pairs(self.build(model="gpt-6-astra")))


class CodexParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_parse_codex_jsonl_rejects_malformed_json_and_ignores_plain_noise(self):
        with self.assertRaisesRegex(ValueError, "malformed JSON"):
            self.module.parse_codex_jsonl('{"type":"turn.completed"')

        stream = "\n".join(
            [
                "loading codex",
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "OK"},
                    }
                ),
                json.dumps({"type": "turn.completed", "usage": {}}),
            ]
        )

        self.assertEqual(self.module.parse_codex_jsonl(stream).text, "OK")

    def test_parse_codex_jsonl_requires_a_completed_turn(self):
        stream = json.dumps(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "OK"}}
        )

        with self.assertRaisesRegex(ValueError, "turn.completed"):
            self.module.parse_codex_jsonl(stream)

    def test_parse_codex_jsonl_surfaces_a_top_level_error_event(self):
        stream = "\n".join(
            [
                json.dumps({"type": "turn.started"}),
                json.dumps({"type": "error", "message": "model not supported"}),
            ]
        )

        with self.assertRaisesRegex(ValueError, "model not supported"):
            self.module.parse_codex_jsonl(stream)


    def test_parse_codex_jsonl_validates_events_after_the_completed_turn(self):
        answered = [
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "OK"}}),
            json.dumps({"type": "turn.completed", "usage": {}}),
        ]
        trailers = [
            (
                "tool-free probe",
                {"type": "item.started", "item": {"type": "file_change", "id": "i1"}},
            ),
            ("late failure", {"type": "error", "message": "late failure"}),
            ("Codex turn failed", {"type": "turn.failed", "error": {"message": "late failure"}}),
        ]

        for expected, trailer in trailers:
            with self.subTest(trailer=trailer["type"]):
                stream = "\n".join(answered + [json.dumps(trailer)])
                with self.assertRaisesRegex(ValueError, expected):
                    self.module.parse_codex_jsonl(stream)

    def test_parse_codex_jsonl_validates_an_item_carried_by_the_completed_turn(self):
        stream = "\n".join(
            [
                json.dumps(
                    {"type": "item.completed", "item": {"type": "agent_message", "text": "OK"}}
                ),
                json.dumps({"type": "turn.completed", "item": {"type": "file_change", "id": "i1"}}),
            ]
        )

        with self.assertRaisesRegex(ValueError, "tool-free probe"):
            self.module.parse_codex_jsonl(stream)

    def test_parse_codex_jsonl_keeps_a_line_separator_inside_an_answer(self):
        answer = {"type": "item.completed", "item": {"type": "agent_message", "text": "A\u2028B"}}
        stream = "\n".join(
            [
                json.dumps(answer, ensure_ascii=False),
                json.dumps({"type": "turn.completed", "usage": {}}),
            ]
        )

        self.assertEqual(self.module.parse_codex_jsonl(stream).text, "A\u2028B")

    def test_codex_failure_reason_keeps_a_line_separator_in_the_message(self):
        stream = json.dumps(
            {"type": "turn.failed", "error": {"message": "A\u2028B"}}, ensure_ascii=False
        )

        self.assertEqual(self.module.codex_failure_reason(stream), "A\u2028B")


class CodexRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def request(self, cwd: Path, **overrides):
        values = {
            "harness": "codex",
            "prompt": "Reply with exactly OK.",
            "timeout_seconds": 30,
            "child_cwd": cwd,
            "model": None,
        }
        values.update(overrides)
        return self.module.HarnessRequest(**values)

    def run_fake(self, behavior: str, **overrides):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw:
            root = Path(raw)
            record = write_fake_codex(root, behavior)
            with mock.patch.dict(os.environ, codex_env(root)):
                result = self.module.run_harness(self.request(root, **overrides))
            argv = record / "argv.json"
            recorded = json.loads(argv.read_text(encoding="utf-8")) if argv.exists() else None
            stdin_file = record / "stdin.bin"
            stdin_bytes = stdin_file.read_bytes() if stdin_file.exists() else None
        return result, recorded, stdin_bytes

    def test_codex_run_takes_the_last_agent_message_and_reports_no_model_identity(self):
        result, _, _ = self.run_fake(CODEX_COMPLETED_TURN)

        self.assertEqual(result.status, self.module.RunStatus.COMPLETED)
        self.assertEqual(result.harness, "codex")
        self.assertEqual(result.harness_version, "codex-cli 0.155.1")
        self.assertEqual(result.assistant.text, "OK")
        self.assertIsNone(result.assistant.provider)
        self.assertIsNone(result.assistant.model)
        self.assertIsNone(result.assistant.stop_reason)

    def test_codex_run_delivers_the_prompt_to_stdin_byte_for_byte(self):
        prompt = (
            "Line one has \"double\" and 'single' quotes.\n"
            "Line two names %TEMP% literally.\n"
            "Line three has ’, € and 中.\n"
            + "padding ’中\n" * 900
            + "final line"
        )
        self.assertGreater(len(prompt.encode("utf-8")), 10240)

        result, argv, stdin_bytes = self.run_fake(CODEX_COMPLETED_TURN, prompt=prompt)

        self.assertEqual(result.status, self.module.RunStatus.COMPLETED)
        self.assertEqual(stdin_bytes, prompt.encode("utf-8"))
        self.assertNotIn(prompt, argv)

    def test_codex_run_reports_the_child_exit_code(self):
        result, _, _ = self.run_fake(
            "print('refused', file=sys.stderr)\nraise SystemExit(3)"
        )

        self.assertEqual(result.status, self.module.RunStatus.CHILD_FAILED)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.stderr.strip(), "refused")

    def test_codex_run_surfaces_a_failed_turn_that_exits_nonzero(self):
        behavior = (
            "print(json.dumps({'type': 'turn.started'}))\n"
            "print(json.dumps({'type': 'turn.failed', 'error': "
            "{'message': 'the model is not supported with a ChatGPT account'}}))\n"
            "raise SystemExit(1)"
        )

        result, _, _ = self.run_fake(behavior)

        self.assertEqual(result.status, self.module.RunStatus.CHILD_FAILED)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not supported with a ChatGPT account", result.error)

    def test_codex_run_rejects_a_turn_that_used_tools(self):
        for item_type in ("command_execution", "file_change"):
            with self.subTest(item_type=item_type):
                behavior = (
                    "print(json.dumps({'type': 'turn.started'}))\n"
                    "print(json.dumps({'type': 'item.started', 'item': "
                    "{'id': 'i1', 'type': '" + item_type + "'}}))\n"
                    "print(json.dumps({'type': 'turn.completed', 'usage': {}}))"
                )

                result, _, _ = self.run_fake(behavior)

                self.assertEqual(result.status, self.module.RunStatus.INVALID_OUTPUT)
                self.assertIn("tool-free probe", result.error)
                self.assertIn(item_type, result.error)

    def test_codex_run_rejects_a_blocked_tool_attempt_reported_only_on_stderr(self):
        # A healthy probe leaves stderr empty. The router line appears only when a tool
        # call was attempted and refused, and it never reaches the JSONL.
        behavior = CODEX_COMPLETED_TURN + (
            'print("2026-09-19T17:27:57.269550Z ERROR codex_core::tools::router: "\n'
            '      "error=patch rejected: writing is blocked by read-only sandbox",\n'
            "      file=sys.stderr)\n"
        )

        result, _, _ = self.run_fake(behavior)

        self.assertEqual(result.status, self.module.RunStatus.INVALID_OUTPUT)
        self.assertIn("blocked tool call", result.error)
        self.assertIn("codex_core::tools::router", result.stderr)

    def test_codex_run_surfaces_a_failed_turn(self):
        behavior = (
            "print(json.dumps({'type': 'turn.started'}))\n"
            "print(json.dumps({'type': 'turn.failed', 'error': "
            "{'message': 'the model is not supported with a ChatGPT account'}}))"
        )

        result, _, _ = self.run_fake(behavior)

        self.assertEqual(result.status, self.module.RunStatus.INVALID_OUTPUT)
        self.assertIn("not supported with a ChatGPT account", result.error)

    def test_codex_run_reports_a_stream_without_a_completed_turn_as_invalid(self):
        behavior = "print(json.dumps({'type': 'thread.started', 'thread_id': 't1'}))"

        result, _, _ = self.run_fake(behavior)

        self.assertEqual(result.status, self.module.RunStatus.INVALID_OUTPUT)
        self.assertIn("turn.completed", result.error)

    def test_codex_run_times_out_and_returns_promptly(self):
        blocked, box = run_with_deadline(
            lambda: self.run_fake("time.sleep(120)", timeout_seconds=1), 45
        )

        self.assertFalse(blocked, "run_harness never returned after the timeout")
        self.assertIsNone(box.get("error"))
        result, _, _ = box["result"]
        self.assertEqual(result.status, self.module.RunStatus.TIMED_OUT)

    def test_codex_run_warns_that_codex_home_agents_md_reaches_the_probe(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw:
            root = Path(raw)
            write_fake_codex(root, CODEX_COMPLETED_TURN)
            environment = codex_env(root)
            agents_md = Path(environment["CODEX_HOME"]) / "AGENTS.md"
            agents_md.write_text("MDT for Codex CLI\n", encoding="utf-8")
            out = root / "run"
            stderr = io.StringIO()
            argv = [
                "--harness", "codex",
                "--prompt", "Reply with exactly OK.",
                "--cwd", str(root),
                "--timeout", "30",
                "--out", str(out),
            ]
            with mock.patch.dict(os.environ, environment):
                with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                    code = self.module.main(argv)
            record = json.loads((out / "result.json").read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(len(record["warnings"]), 1)
        self.assertIn("AGENTS.md", record["warnings"][0])
        self.assertIn("--ignore-user-config", record["warnings"][0])
        self.assertIn(record["warnings"][0], stderr.getvalue())

    def test_codex_run_reports_no_warning_when_codex_home_has_no_agents_md(self):
        result, _, _ = self.run_fake(CODEX_COMPLETED_TURN)

        self.assertEqual(result.status, self.module.RunStatus.COMPLETED)
        self.assertEqual(result.warnings, ())


    def test_main_sends_prompt_file_bytes_to_the_child_unchanged(self):
        exact = b"A\r\nB\rC\ncaf\xc3\xa9"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw:
            root = Path(raw)
            record = write_fake_codex(root, CODEX_COMPLETED_TURN)
            prompt_file = root / "prompt.txt"
            prompt_file.write_bytes(exact)
            out = root / "run"
            argv = [
                "--harness", "codex",
                "--prompt-file", str(prompt_file),
                "--cwd", str(root),
                "--timeout", "30",
                "--out", str(out),
            ]
            with mock.patch.dict(os.environ, codex_env(root)):
                with contextlib.redirect_stderr(io.StringIO()):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = self.module.main(argv)
            delivered = (record / "stdin.bin").read_bytes()

        self.assertEqual(code, 0)
        self.assertEqual(delivered, exact)


class ProcessTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    @unittest.skipUnless(os.name == "nt", "process-tree teardown is the Windows path")
    def test_timeout_returns_when_a_grandchild_still_holds_the_pipes(self):
        behavior = """
        if "--version" in sys.argv:
            print("omp/18.1.21")
            raise SystemExit(0)
        pidfile = HERE / "descendant-pids.txt"
        with open(pidfile, "a", encoding="utf-8") as handle:
            print(os.getpid(), file=handle)
        subprocess.Popen([sys.executable, str(HERE / "sleeper.py"), str(pidfile)])
        time.sleep(120)
        """
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw:
            root = Path(raw)
            pidfile = write_sleeping_grandchild(root)
            write_shim(root, "omp", behavior)
            request = self.module.HarnessRequest(
                harness="omp",
                prompt="Reply with exactly OK.",
                timeout_seconds=1,
                child_cwd=root,
                model=None,
            )

            def call():
                with mock.patch.dict(
                    os.environ, {"PATH": str(root) + os.pathsep + os.environ["PATH"]}
                ):
                    return self.module.run_harness(request)

            blocked, box = run_with_deadline(call, 45)
            reap(pidfile)

        self.assertFalse(blocked, "run_harness never returned after the timeout")
        self.assertIsNone(box.get("error"))
        self.assertEqual(box["result"].status, self.module.RunStatus.TIMED_OUT)


if __name__ == "__main__":
    unittest.main()
