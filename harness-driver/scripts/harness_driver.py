#!/usr/bin/env python3
"""Run one isolated, tool-free prompt against a supported agent harness."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = 1


class RunStatus(str, Enum):
    COMPLETED = "completed"
    CHILD_FAILED = "child_failed"
    TIMED_OUT = "timed_out"
    INVALID_OUTPUT = "invalid_output"
    LAUNCH_FAILED = "launch_failed"


@dataclass(frozen=True)
class HarnessRequest:
    harness: str
    prompt: str
    timeout_seconds: int
    child_cwd: Path
    model: Optional[str] = None


@dataclass(frozen=True)
class AssistantReply:
    text: str
    provider: Optional[str]
    model: Optional[str]
    stop_reason: Optional[str]


@dataclass(frozen=True)
class HarnessResult:
    harness: str
    harness_version: Optional[str]
    executable: Optional[str]
    status: RunStatus
    exit_code: Optional[int]
    duration_ms: int
    assistant: Optional[AssistantReply]
    stdout: str
    stderr: str
    error: Optional[str]
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class HarnessAdapter:
    name: str
    binary: str
    prompt_via_stdin: bool
    build_command: Callable[[HarnessRequest, str], List[str]]
    parse_output: Callable[[str], AssistantReply]
    ambient_warnings: Callable[[], List[str]]
    failure_reason: Callable[[str], Optional[str]]
    stderr_rejection: Callable[[str], Optional[str]]


def build_omp_command(request: HarnessRequest, executable: str) -> List[str]:
    command = [
        executable,
        "-p",
        "--mode=json",
        "--no-tools",
        "--no-session",
        "--no-extensions",
        "--no-skills",
        "--no-rules",
        "--system-prompt=Follow the user message. Answer the task directly.",
        "--cwd={}".format(request.child_cwd.resolve()),
    ]
    if request.model:
        command.append("--model={}".format(request.model))
    command.append(request.prompt)
    return command


def parse_omp_jsonl(output: str) -> AssistantReply:
    events = []
    for line in output.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except ValueError as error:
            if stripped.startswith("{") or stripped.startswith("["):
                raise ValueError("OMP emitted malformed JSON: {}".format(error))
            continue
        if isinstance(event, dict):
            events.append(event)

    turn_index = None
    turn = None
    for index, event in enumerate(events):
        if event.get("type") == "turn_end":
            turn_index = index
            turn = event
    if turn is None:
        raise ValueError("OMP output has no turn_end event")

    terminal = any(
        event.get("type") == "agent_end" and event.get("isTerminal") is True
        for event in events[turn_index + 1 :]
    )
    if not terminal:
        raise ValueError("OMP output has no terminal agent_end event after the final turn_end")
    if any(event.get("toolResults") for event in events):
        raise ValueError("OMP used tools during a tool-free probe")

    message = turn.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        raise ValueError("OMP turn_end has no assistant message")
    content = message.get("content")
    if not isinstance(content, list):
        raise ValueError("OMP assistant message has no content list")
    text = "".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    )
    if not text:
        raise ValueError("OMP assistant message has no text content")
    return AssistantReply(
        text=text,
        provider=message.get("provider") if isinstance(message.get("provider"), str) else None,
        model=message.get("model") if isinstance(message.get("model"), str) else None,
        stop_reason=(
            message.get("stopReason") if isinstance(message.get("stopReason"), str) else None
        ),
    )


CODEX_ISOLATION_FLAGS = (
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

CODEX_PROBE_ITEM_TYPES = frozenset({"agent_message", "reasoning", "error"})


def build_codex_command(request: HarnessRequest, executable: str) -> List[str]:
    command = [
        executable,
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "-s",
        "read-only",
        "-C",
        str(request.child_cwd.resolve()),
    ]
    for flag, value in CODEX_ISOLATION_FLAGS:
        command.extend([flag, value])
    if request.model:
        command.extend(["-m", request.model])
    command.append("-")
    return command


def parse_codex_jsonl(output: str) -> AssistantReply:
    events = []
    for line in output.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except ValueError as error:
            if stripped.startswith("{") or stripped.startswith("["):
                raise ValueError("Codex emitted malformed JSON: {}".format(error))
            continue
        if isinstance(event, dict):
            events.append(event)

    # Scanning past the completed turn is the point: a tool item or a failure that
    # arrives after it still means the probe was not tool-free.
    answer = None
    completed = False
    for event in events:
        kind = event.get("type")
        if kind == "turn.failed":
            failure = event.get("error")
            message = failure.get("message") if isinstance(failure, dict) else None
            raise ValueError("Codex turn failed: {}".format(message))
        if kind == "error":
            raise ValueError("Codex reported an error: {}".format(event.get("message")))
        item = event.get("item")
        if isinstance(item, dict):
            item_type = item.get("type")
            if item_type not in CODEX_PROBE_ITEM_TYPES:
                raise ValueError(
                    "Codex used tools during a tool-free probe: {}".format(item_type)
                )
            if item_type == "agent_message" and not completed:
                text = item.get("text")
                if isinstance(text, str) and text:
                    answer = text
        if kind == "turn.completed":
            if answer is None:
                raise ValueError("Codex turn has no agent_message text")
            completed = True
    if not completed:
        raise ValueError("Codex output has no turn.completed event")
    return AssistantReply(text=answer, provider=None, model=None, stop_reason=None)


def codex_failure_reason(output: str) -> Optional[str]:
    events = []
    for line in output.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)

    for event in events:
        if event.get("type") == "turn.failed":
            failure = event.get("error")
            message = failure.get("message") if isinstance(failure, dict) else None
            if isinstance(message, str) and message:
                return message
    for event in events:
        if event.get("type") == "error":
            message = event.get("message")
            if isinstance(message, str) and message:
                return message
    return None


def _no_failure_reason(output: str) -> Optional[str]:
    return None


CODEX_ROUTER_ERROR = "ERROR codex_core::tools::router:"


def codex_stderr_rejection(stderr: str) -> Optional[str]:
    # A refused tool call is reported here and nowhere else, so a stream that looks
    # tool-free is not on its own evidence that no tool was reached for.
    for line in stderr.split("\n"):
        if CODEX_ROUTER_ERROR in line:
            return "codex attempted a blocked tool call during a tool-free probe: {}".format(
                line.strip()
            )
    return None


def _no_stderr_rejection(stderr: str) -> Optional[str]:
    return None


def codex_ambient_warnings() -> List[str]:
    configured = os.environ.get("CODEX_HOME")
    codex_home = Path(configured) if configured else Path.home() / ".codex"
    agents_md = codex_home / "AGENTS.md"
    if not agents_md.is_file():
        return []
    return [
        "codex loads {} even under --ignore-user-config, "
        "so its text reaches the probe".format(agents_md)
    ]


def _no_ambient_warnings() -> List[str]:
    return []


ADAPTERS = {
    "omp": HarnessAdapter(
        name="omp",
        binary="omp",
        prompt_via_stdin=False,
        build_command=build_omp_command,
        parse_output=parse_omp_jsonl,
        ambient_warnings=_no_ambient_warnings,
        failure_reason=_no_failure_reason,
        stderr_rejection=_no_stderr_rejection,
    ),
    "codex": HarnessAdapter(
        name="codex",
        binary="codex",
        prompt_via_stdin=True,
        build_command=build_codex_command,
        parse_output=parse_codex_jsonl,
        ambient_warnings=codex_ambient_warnings,
        failure_reason=codex_failure_reason,
        stderr_rejection=codex_stderr_rejection,
    ),
}


def _read_version(executable: str) -> Optional[str]:
    try:
        process = subprocess.Popen(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            start_new_session=(os.name == "posix"),
        )
    except OSError:
        return None
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            _kill_process(process)
            process.communicate(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return None
    if process.returncode != 0:
        return None
    version = stdout.strip() or stderr.strip()
    return version or None


def _kill_tree(process: subprocess.Popen) -> None:
    # Killing only the launched process leaves grandchildren holding the inherited
    # stdout and stderr pipes, so the post-kill communicate() never returns.
    try:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    process.kill()


def _stop_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        _kill_tree(process)


def _kill_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
    else:
        _kill_tree(process)


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_harness(request: HarnessRequest) -> HarnessResult:
    started = time.monotonic()
    adapter = ADAPTERS.get(request.harness)
    if adapter is None:
        raise ValueError("unsupported harness: {}".format(request.harness))
    if request.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    child_cwd = request.child_cwd.resolve()
    if not child_cwd.is_dir():
        raise ValueError("child_cwd is not a directory: {}".format(child_cwd))
    warnings = tuple(adapter.ambient_warnings())

    executable = shutil.which(adapter.binary)
    if executable is None:
        return HarnessResult(
            harness=adapter.name,
            harness_version=None,
            executable=None,
            status=RunStatus.LAUNCH_FAILED,
            exit_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            assistant=None,
            stdout="",
            stderr="",
            error="{} executable not found on PATH".format(adapter.binary),
            warnings=warnings,
        )

    version = _read_version(executable)
    command = adapter.build_command(request, executable)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(child_cwd),
            stdin=subprocess.PIPE if adapter.prompt_via_stdin else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            start_new_session=(os.name == "posix"),
        )
    except OSError as error:
        return HarnessResult(
            harness=adapter.name,
            harness_version=version,
            executable=executable,
            status=RunStatus.LAUNCH_FAILED,
            exit_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            assistant=None,
            stdout="",
            stderr="",
            error=str(error),
            warnings=warnings,
        )

    stdin_payload = None
    if adapter.prompt_via_stdin:
        # Text-mode stdin rewrites "\n" as os.linesep, which would reshape the prompt.
        process.stdin.reconfigure(newline="")
        stdin_payload = request.prompt
    try:
        stdout, stderr = process.communicate(
            input=stdin_payload, timeout=request.timeout_seconds
        )
    except subprocess.TimeoutExpired as timeout_error:
        _stop_process(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired as stop_timeout:
            _kill_process(process)
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired as kill_timeout:
                stdout, stderr = kill_timeout.stdout, kill_timeout.stderr
            stdout = _text(stdout) or _text(stop_timeout.stdout)
            stderr = _text(stderr) or _text(stop_timeout.stderr)
        stdout = _text(stdout) or _text(timeout_error.stdout)
        stderr = _text(stderr) or _text(timeout_error.stderr)
        return HarnessResult(
            harness=adapter.name,
            harness_version=version,
            executable=executable,
            status=RunStatus.TIMED_OUT,
            exit_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error="timed out after {}s".format(request.timeout_seconds),
            warnings=warnings,
        )

    duration_ms = int((time.monotonic() - started) * 1000)
    if process.returncode != 0:
        error = "{} exited with code {}".format(adapter.name, process.returncode)
        reason = adapter.failure_reason(stdout)
        if reason:
            error = "{}: {}".format(error, reason)
        return HarnessResult(
            harness=adapter.name,
            harness_version=version,
            executable=executable,
            status=RunStatus.CHILD_FAILED,
            exit_code=process.returncode,
            duration_ms=duration_ms,
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error=error,
            warnings=warnings,
        )
    try:
        assistant = adapter.parse_output(stdout)
    except ValueError as error:
        return HarnessResult(
            harness=adapter.name,
            harness_version=version,
            executable=executable,
            status=RunStatus.INVALID_OUTPUT,
            exit_code=process.returncode,
            duration_ms=duration_ms,
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error=str(error),
            warnings=warnings,
        )
    rejection = adapter.stderr_rejection(stderr)
    if rejection:
        return HarnessResult(
            harness=adapter.name,
            harness_version=version,
            executable=executable,
            status=RunStatus.INVALID_OUTPUT,
            exit_code=process.returncode,
            duration_ms=duration_ms,
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error=rejection,
            warnings=warnings,
        )
    return HarnessResult(
        harness=adapter.name,
        harness_version=version,
        executable=executable,
        status=RunStatus.COMPLETED,
        exit_code=process.returncode,
        duration_ms=duration_ms,
        assistant=assistant,
        stdout=stdout,
        stderr=stderr,
        error=None,
        warnings=warnings,
    )


def result_record(result: HarnessResult) -> dict:
    assistant = None
    if result.assistant is not None:
        assistant = {
            "text": result.assistant.text,
            "provider": result.assistant.provider,
            "model": result.assistant.model,
            "stop_reason": result.assistant.stop_reason,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "harness": result.harness,
        "harness_version": result.harness_version,
        "executable": result.executable,
        "status": result.status.value,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "assistant": assistant,
        "events_file": "events.jsonl",
        "stderr_file": "stderr.txt",
        "answer_file": "answer.txt" if result.assistant is not None else None,
        "error": result.error,
        "warnings": list(result.warnings),
    }


def write_result(directory: Path, result: HarnessResult) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "events.jsonl").write_text(result.stdout, encoding="utf-8")
    (directory / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.assistant is not None:
        (directory / "answer.txt").write_text(result.assistant.text + "\n", encoding="utf-8")
    (directory / "result.json").write_text(
        json.dumps(result_record(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", default="omp", choices=sorted(ADAPTERS))
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt")
    prompt.add_argument("--prompt-file")
    parser.add_argument("--cwd", required=True, help="Empty or disposable child working directory.")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--model")
    parser.add_argument("--out", required=True, help="New directory for run evidence.")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.out).resolve()
    if output_dir.exists():
        print("output directory already exists: {}".format(output_dir), file=os.sys.stderr)
        return 2
    child_cwd = Path(args.cwd).resolve()
    if not child_cwd.is_dir():
        print("child cwd is not a directory: {}".format(child_cwd), file=os.sys.stderr)
        return 2
    if args.prompt_file:
        try:
            # read_text() translates CRLF and lone CR to LF, which the stdin writer
            # downstream has no way to restore.
            prompt = Path(args.prompt_file).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            print(str(error), file=os.sys.stderr)
            return 2
    else:
        prompt = args.prompt
    result = run_harness(
        HarnessRequest(
            harness=args.harness,
            prompt=prompt,
            timeout_seconds=args.timeout,
            child_cwd=child_cwd,
            model=args.model,
        )
    )
    try:
        write_result(output_dir, result)
    except FileExistsError:
        print("output directory already exists: {}".format(output_dir), file=os.sys.stderr)
        return 2
    for warning in result.warnings:
        print("warning: {}".format(warning), file=os.sys.stderr)
    print("{}: {}".format(result.status.value, output_dir))
    return 0 if result.status is RunStatus.COMPLETED else 1


if __name__ == "__main__":
    raise SystemExit(main())
