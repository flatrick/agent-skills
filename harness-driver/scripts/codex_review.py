#!/usr/bin/env python3
"""Hand a prompt file to Codex for a read-only review of a git worktree.

Unlike harness_driver.py, which runs tool-free probes, a review needs Codex to
read the repository, so its shell tool stays enabled. The sandbox is always
read-only: this script has no mode that lets Codex write.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_driver import (  # noqa: E402
    RunStatus,
    _force_utf8_streams,
    _kill_process,
    _stop_process,
    _text,
    _write_evidence,
    codex_failure_reason,
)


@dataclass(frozen=True)
class ReviewRequest:
    worktree: Path
    prompt: str
    timeout_seconds: int
    model: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class ReviewResult:
    status: RunStatus
    exit_code: Optional[int]
    duration_ms: int
    answer: Optional[str]
    stdout: str
    stderr: str
    error: Optional[str]


def build_command(request: ReviewRequest, executable: str) -> List[str]:
    command = [
        executable,
        "exec",
        "--json",
        "--ephemeral",
        # A user config can route approval requests to an automatic reviewer, which
        # re-runs a sandbox-blocked command outside the read-only sandbox.
        "--ignore-user-config",
    ]
    if sys.platform == "win32":
        # Without it the read-only sandbox cannot start on Windows, and every command,
        # reads included, is rejected by policy.
        command.extend(["-c", 'windows.sandbox="elevated"'])
    command.extend(["--skip-git-repo-check", "-s", "read-only", "-C", str(request.worktree)])
    if request.model:
        command.extend(["-m", request.model])
    command.append("-")
    return command


def review_stdin(request: ReviewRequest) -> str:
    """The harness note, if any, then the prompt file's text unchanged.

    The note travels on stdin because the codex.cmd shim hands its arguments to cmd.exe,
    which splits them at characters such as "&" that paths and commands contain.
    """
    if not request.note:
        return request.prompt
    return (
        "[Harness note: facts about this environment, not part of the task]\n"
        + request.note
        + "[End of harness note. The task follows.]\n\n"
        + request.prompt
    )


PythonInterpreter = Tuple[str, str]


def python_candidates() -> List[str]:
    candidates = [sys.executable]
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    return candidates


def probe_python(executable: str) -> Optional[PythonInterpreter]:
    """Ask a candidate which interpreter it runs, which resolves launchers and aliases."""
    try:
        process = subprocess.Popen(
            [executable, "-B", "-c", "import platform, sys; print(sys.executable); print(platform.python_version())"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=(os.name == "posix"),
        )
    except OSError:
        return None
    try:
        stdout, _ = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            _kill_process(process)
            process.communicate(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return None
    lines = stdout.decode("utf-8", errors="replace").split("\n")
    if process.returncode != 0 or len(lines) < 2 or not lines[0].strip():
        return None
    return lines[0].strip(), lines[1].strip()


def discover_pythons(candidates: Sequence[str], probe=probe_python) -> List[PythonInterpreter]:
    found = {}
    for candidate in candidates:
        interpreter = probe(candidate)
        if interpreter is not None:
            found.setdefault(os.path.normcase(interpreter[0]), interpreter)
    return list(found.values())


def python_note(interpreters: Sequence[PythonInterpreter]) -> Optional[str]:
    """Tell Codex where Python is and how to run it; the task decides which one it needs."""
    if not interpreters:
        return None
    if sys.platform == "win32":
        call = "& '{}'".format(interpreters[0][0].replace("'", "''"))
    else:
        call = "'{}'".format(interpreters[0][0].replace("'", "'\\''"))
    lines = ["Python interpreters found on this machine before the run:"]
    lines.extend("- {} (Python {})".format(path, version) for path, version in interpreters)
    lines.append("Run one by its full path, for example: {} -B -c \"print('ok')\"".format(call))
    lines.append("A bare `python` or `py` command may resolve to a launcher that cannot start inside the sandbox.")
    lines.append("The sandbox is read-only: -B stops Python writing bytecode, and tools that write caches, such as uv, fail.")
    return "\n".join(lines) + "\n"


def final_answer(output: str) -> str:
    """Return the last completed agent message of the final turn, which must have completed.

    Tool use is expected. Anything after the final turn.completed other than a new
    turn means the stream is not a finished run.
    """
    answer = None
    completed = False
    for line in output.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            event = json.loads(stripped)
        except ValueError as error:
            raise ValueError("Codex emitted malformed JSON: {}".format(error))
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "turn.failed":
            failure = event.get("error")
            message = failure.get("message") if isinstance(failure, dict) else None
            raise ValueError("Codex turn failed: {}".format(message))
        if kind == "turn.started":
            answer = None
            completed = False
            continue
        if kind == "turn.completed":
            completed = True
            continue
        if isinstance(kind, str) and kind.startswith("item.") and completed:
            raise ValueError("Codex emitted {} after turn.completed without a new turn".format(kind))
        item = event.get("item")
        if kind == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str) and text:
                answer = text
    if not completed:
        raise ValueError("Codex output has no turn.completed event")
    if answer is None:
        raise ValueError("Codex turn has no agent_message text")
    return answer


def _git(worktree: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(worktree), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout


def default_evidence_root(worktree: Path) -> Path:
    """Main checkout's .scratch/, plus the worktree's name when run from a linked worktree.

    The main checkout is the first entry of `git worktree list --porcelain`, which
    reports it correctly from inside any linked worktree.
    """
    main = main_checkout(worktree)
    current = Path(_git(worktree, "rev-parse", "--show-toplevel").strip()).resolve()
    scratch = main / ".scratch"
    if current != main:
        scratch = scratch / current.name
    return scratch / "codex"


def main_checkout(worktree: Path) -> Path:
    first = _git(worktree, "worktree", "list", "--porcelain").split("\n", 1)[0]
    if not first.startswith("worktree "):
        raise ValueError("unexpected git worktree list output: {!r}".format(first))
    return Path(first[len("worktree "):]).resolve()


def run_review(request: ReviewRequest, executable: str) -> ReviewResult:
    return run_codex(build_command(request, executable), request.worktree, review_stdin(request), request.timeout_seconds)


def run_codex(command: List[str], cwd: Path, prompt: str, timeout_seconds: int) -> ReviewResult:
    """Run a codex exec command with the prompt on stdin and parse its final answer."""
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            # _stop_process signals the process group on POSIX, which needs its own session.
            start_new_session=(os.name == "posix"),
        )
    except OSError as error:
        return ReviewResult(RunStatus.LAUNCH_FAILED, None, 0, None, "", "", str(error))

    # Text-mode stdin rewrites "\n" as os.linesep, which would reshape the prompt.
    process.stdin.reconfigure(newline="")
    try:
        stdout, stderr = process.communicate(input=prompt, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as timeout_error:
        stdout, stderr = None, None
        try:
            _stop_process(process)
            stdout, stderr = process.communicate(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                _kill_process(process)
                stdout, stderr = process.communicate(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as kill_error:
                # A descendant still holding the pipes keeps communicate() waiting;
                # report the timeout with whatever output arrived rather than raising.
                if isinstance(kill_error, subprocess.TimeoutExpired):
                    stdout, stderr = kill_error.stdout, kill_error.stderr
        return ReviewResult(
            RunStatus.TIMED_OUT,
            None,
            int((time.monotonic() - started) * 1000),
            None,
            _text(stdout) or _text(timeout_error.stdout),
            _text(stderr) or _text(timeout_error.stderr),
            "timed out after {}s".format(timeout_seconds),
        )

    duration_ms = int((time.monotonic() - started) * 1000)
    if process.returncode != 0:
        error = "codex exited with code {}".format(process.returncode)
        reason = codex_failure_reason(stdout)
        if reason:
            error = "{}: {}".format(error, reason)
        return ReviewResult(RunStatus.CHILD_FAILED, process.returncode, duration_ms, None, stdout, stderr, error)
    try:
        answer = final_answer(stdout)
    except ValueError as error:
        return ReviewResult(RunStatus.INVALID_OUTPUT, process.returncode, duration_ms, None, stdout, stderr, str(error))
    return ReviewResult(RunStatus.COMPLETED, process.returncode, duration_ms, answer, stdout, stderr, None)


def write_evidence(
    directory: Path, prompt: str, worktree: Path, result: ReviewResult, stdin: Optional[str] = None
) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    _write_evidence(directory / "prompt.txt", prompt)
    if stdin is not None:
        _write_evidence(directory / "stdin.txt", stdin)
    _write_evidence(directory / "events.jsonl", result.stdout)
    _write_evidence(directory / "stderr.txt", result.stderr)
    if result.answer is not None:
        _write_evidence(directory / "answer.txt", result.answer + "\n")
    record = {
        "worktree": str(worktree),
        "sandbox": "read-only",
        "status": result.status.value,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }
    _write_evidence(directory / "result.json", json.dumps(record, indent=2, sort_keys=True) + "\n")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", required=True, help="The handoff: the review request, as a file.")
    parser.add_argument("--worktree", required=True, help="Git worktree Codex reviews, read-only.")
    parser.add_argument("--label", default="review", help="Evidence directory name prefix.")
    parser.add_argument("--out", help="Evidence directory. Default: <main checkout>/.scratch/<worktree>/codex/<label>-<timestamp>.")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--model")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    _force_utf8_streams()
    args = parse_args(argv)
    worktree = Path(args.worktree).resolve()
    if not worktree.is_dir():
        print("worktree is not a directory: {}".format(worktree), file=sys.stderr)
        return 2
    try:
        # read_text() translates CRLF and lone CR to LF, which stdin cannot restore.
        prompt = Path(args.prompt_file).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        if args.out:
            out = Path(args.out).resolve()
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            out = default_evidence_root(worktree) / "{}-{}".format(args.label, stamp)
    except (subprocess.CalledProcessError, ValueError) as error:
        print("cannot resolve the evidence directory: {}".format(error), file=sys.stderr)
        return 2
    if out.exists():
        print("evidence directory already exists: {}".format(out), file=sys.stderr)
        return 2

    note = python_note(discover_pythons(python_candidates()))
    executable = shutil.which("codex")
    request = ReviewRequest(worktree, prompt, args.timeout, args.model, note)
    if executable is None:
        result = ReviewResult(RunStatus.LAUNCH_FAILED, None, 0, None, "", "", "codex executable not found on PATH")
    else:
        result = run_review(request, executable)
    write_evidence(out, prompt, worktree, result, review_stdin(request))

    print("{}: {}".format(result.status.value, out))
    if result.error:
        print("error: {}".format(result.error))
    if result.answer is not None:
        print()
        print(result.answer)
    return 0 if result.status is RunStatus.COMPLETED else 1


if __name__ == "__main__":
    raise SystemExit(main())
