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
from typing import List, Optional, Sequence


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
    for line in output.splitlines():
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
    if turn.get("toolResults"):
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


def _read_version(executable: str) -> Optional[str]:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    version = completed.stdout.strip() or completed.stderr.strip()
    return version or None


def _stop_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()


def _kill_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
    else:
        process.kill()


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_harness(request: HarnessRequest) -> HarnessResult:
    started = time.monotonic()
    if request.harness != "omp":
        raise ValueError("unsupported harness: {}".format(request.harness))
    if request.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    child_cwd = request.child_cwd.resolve()
    if not child_cwd.is_dir():
        raise ValueError("child_cwd is not a directory: {}".format(child_cwd))

    executable = shutil.which("omp")
    if executable is None:
        return HarnessResult(
            harness="omp",
            harness_version=None,
            executable=None,
            status=RunStatus.LAUNCH_FAILED,
            exit_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            assistant=None,
            stdout="",
            stderr="",
            error="omp executable not found on PATH",
        )

    version = _read_version(executable)
    command = build_omp_command(request, executable)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(child_cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=(os.name == "posix"),
        )
    except OSError as error:
        return HarnessResult(
            harness="omp",
            harness_version=version,
            executable=executable,
            status=RunStatus.LAUNCH_FAILED,
            exit_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            assistant=None,
            stdout="",
            stderr="",
            error=str(error),
        )

    try:
        stdout, stderr = process.communicate(timeout=request.timeout_seconds)
    except subprocess.TimeoutExpired as timeout_error:
        _stop_process(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _kill_process(process)
            stdout, stderr = process.communicate()
        stdout = _text(stdout) or _text(timeout_error.stdout)
        stderr = _text(stderr) or _text(timeout_error.stderr)
        return HarnessResult(
            harness="omp",
            harness_version=version,
            executable=executable,
            status=RunStatus.TIMED_OUT,
            exit_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error="timed out after {}s".format(request.timeout_seconds),
        )

    duration_ms = int((time.monotonic() - started) * 1000)
    if process.returncode != 0:
        return HarnessResult(
            harness="omp",
            harness_version=version,
            executable=executable,
            status=RunStatus.CHILD_FAILED,
            exit_code=process.returncode,
            duration_ms=duration_ms,
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error="OMP exited with code {}".format(process.returncode),
        )
    try:
        assistant = parse_omp_jsonl(stdout)
    except ValueError as error:
        return HarnessResult(
            harness="omp",
            harness_version=version,
            executable=executable,
            status=RunStatus.INVALID_OUTPUT,
            exit_code=process.returncode,
            duration_ms=duration_ms,
            assistant=None,
            stdout=stdout,
            stderr=stderr,
            error=str(error),
        )
    return HarnessResult(
        harness="omp",
        harness_version=version,
        executable=executable,
        status=RunStatus.COMPLETED,
        exit_code=process.returncode,
        duration_ms=duration_ms,
        assistant=assistant,
        stdout=stdout,
        stderr=stderr,
        error=None,
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
    parser.add_argument("--harness", default="omp", choices=["omp"])
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
            prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        except OSError as error:
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
    print("{}: {}".format(result.status.value, output_dir))
    return 0 if result.status is RunStatus.COMPLETED else 1


if __name__ == "__main__":
    raise SystemExit(main())
