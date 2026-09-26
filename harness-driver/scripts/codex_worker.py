#!/usr/bin/env python3
"""Hand a prompt file to Codex as a code-writing worker in a throwaway git worktree.

Codex runs under -s danger-full-access, because on Windows the workspace-write
sandbox leaves files the invoking user cannot read (see references/codex.md).
That means no operating-system sandbox, so the script refuses to run without
--unsandboxed. The worktree is a diff boundary, not containment: writes outside
it are only detected, for the supervising worktree, and reported as warnings.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_review import (  # noqa: E402
    ReviewResult,
    _git,
    default_evidence_root,
    main_checkout,
    run_codex,
)
from harness_driver import RunStatus, _force_utf8_streams, _write_evidence  # noqa: E402


@dataclass(frozen=True)
class WorkerRequest:
    worktree: Path
    prompt: str
    timeout_seconds: int
    model: Optional[str] = None
    project_docs: bool = True


def build_command(request: WorkerRequest, executable: str) -> List[str]:
    command = [
        executable,
        "exec",
        "--json",
        "--ephemeral",
        "--skip-git-repo-check",
        "-s",
        "danger-full-access",
        "-C",
        str(request.worktree),
    ]
    if not request.project_docs:
        command.extend(["-c", "project_doc_max_bytes=0"])
    if request.model:
        command.extend(["-m", request.model])
    command.append("-")
    return command


def run_worker(request: WorkerRequest, executable: str) -> ReviewResult:
    return run_codex(build_command(request, executable), request.worktree, request.prompt, request.timeout_seconds)


def create_worktree(repo: Path, root: Path, name: str, base_sha: str) -> Path:
    path = root / name
    _git(repo, "worktree", "add", "--detach", str(path), base_sha)
    return path.resolve()


def _git_bytes(worktree: Path, *args: str) -> bytes:
    # Bytes, not text: a patch must keep CRLF and non-UTF-8 content exactly as staged.
    return subprocess.run(["git", "-C", str(worktree), *args], check=True, capture_output=True).stdout


def _paths(raw: bytes) -> List[str]:
    return [os.fsdecode(entry) for entry in raw.split(b"\0") if entry]


@dataclass(frozen=True)
class Collected:
    patch: bytes
    status: bytes
    changed_files: List[str]
    ignored_files: List[str]


def collect(worktree: Path, base_sha: str) -> Collected:
    """Stage everything and diff against the base, so commits Codex made are included.

    `git add -A` skips ignored files, so they are listed separately rather than lost.
    """
    # If the worker removed the worktree's .git file, git would walk up to the enclosing repo.
    toplevel = Path(os.fsdecode(_git_bytes(worktree, "rev-parse", "--show-toplevel")).strip()).resolve()
    if toplevel != worktree:
        raise OSError("the throwaway worktree is no longer its own git toplevel (git resolved {})".format(toplevel))
    _git_bytes(worktree, "add", "-A")
    return Collected(
        patch=_git_bytes(worktree, "diff", "--cached", "--binary", base_sha),
        status=_git_bytes(worktree, "status", "--porcelain"),
        changed_files=_paths(_git_bytes(worktree, "diff", "--cached", "--name-only", "-z", base_sha)),
        ignored_files=_paths(_git_bytes(worktree, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")),
    )


def fingerprint(repo: Path, exclude: Path) -> Dict[str, Tuple[int, int]]:
    """Size and mtime of every modified, untracked and ignored file in the repo.

    Comparing status text alone misses a second write to an already-dirty file or a
    write under an ignored directory; sizes and mtimes catch both.
    """
    entries = _git_bytes(repo, "status", "--porcelain=v1", "-z", "--ignored=matching", "-uall").split(b"\0")
    result: Dict[str, Tuple[int, int]] = {}
    skip_next = False
    for entry in entries:
        if skip_next:
            skip_next = False
            continue
        if len(entry) < 4:
            continue
        if entry[:1] in (b"R", b"C"):
            skip_next = True
        relative = os.fsdecode(entry[3:])
        path = (repo / relative).resolve()
        if path == exclude or exclude in path.parents:
            continue
        try:
            stat = path.stat()
            result[relative] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            result[relative] = (-1, -1)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", required=True, help="The handoff: the task, as a file.")
    parser.add_argument("--repo", required=True, help="Supervising git worktree; the throwaway worktree branches from it.")
    parser.add_argument("--base", default="HEAD", help="Commit-ish the throwaway worktree starts from.")
    parser.add_argument("--label", default="worker", help="Worktree and evidence directory name prefix.")
    parser.add_argument("--worktree-root", help="Where the throwaway worktree goes. Default: <main checkout>/.worktrees.")
    parser.add_argument("--out", help="Evidence directory. Default: <main checkout>/.scratch/<worktree>/codex/<label>-<timestamp>.")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--model")
    parser.add_argument("--no-project-docs", action="store_true", help="Keep repository AGENTS.md files out of Codex's context.")
    parser.add_argument("--unsandboxed", action="store_true", help="Required: acknowledges Codex runs with danger-full-access.")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def write_evidence(directory: Path, prompt: str, record: dict, result: ReviewResult, collected: Optional[Collected]) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    _write_evidence(directory / "prompt.txt", prompt)
    _write_evidence(directory / "events.jsonl", result.stdout)
    _write_evidence(directory / "stderr.txt", result.stderr)
    if result.answer is not None:
        _write_evidence(directory / "answer.txt", result.answer + "\n")
    if collected is not None:
        (directory / "patch.diff").write_bytes(collected.patch)
        (directory / "status.txt").write_bytes(collected.status)
        _write_evidence(directory / "ignored.txt", "".join(path + "\n" for path in collected.ignored_files))
    _write_evidence(directory / "result.json", json.dumps(record, indent=2, sort_keys=True) + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    _force_utf8_streams()
    args = parse_args(argv)
    if not args.unsandboxed:
        print("refusing to run: Codex workers run with danger-full-access; pass --unsandboxed to accept that", file=sys.stderr)
        return 2
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print("repo is not a directory: {}".format(repo), file=sys.stderr)
        return 2
    try:
        prompt = Path(args.prompt_file).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = "codex-{}-{}".format(args.label, stamp)
    try:
        base_sha = _git(repo, "rev-parse", "--verify", args.base + "^{commit}").strip()
        root = Path(args.worktree_root).resolve() if args.worktree_root else main_checkout(repo) / ".worktrees"
        out = Path(args.out).resolve() if args.out else default_evidence_root(repo) / "{}-{}".format(args.label, stamp)
    except (subprocess.CalledProcessError, ValueError) as error:
        print("cannot resolve the base, worktree root or evidence directory: {}".format(error), file=sys.stderr)
        return 2
    if out.exists():
        print("evidence directory already exists: {}".format(out), file=sys.stderr)
        return 2
    executable = shutil.which("codex")
    if executable is None:
        print("codex executable not found on PATH", file=sys.stderr)
        return 2

    try:
        worktree = create_worktree(repo, root, name, base_sha)
    except subprocess.CalledProcessError as error:
        print("git worktree add failed: {}".format(error.stderr), file=sys.stderr)
        return 2
    before = fingerprint(repo, worktree)
    result = run_worker(WorkerRequest(worktree, prompt, args.timeout, args.model, not args.no_project_docs), executable)

    warnings = []
    collected = None
    collection_error = None
    try:
        if fingerprint(repo, worktree) != before:
            warnings.append("the supervising worktree changed during the run: a write landed outside the throwaway worktree")
        collected = collect(worktree, base_sha)
    except (subprocess.CalledProcessError, OSError) as error:
        stderr = getattr(error, "stderr", None)
        collection_error = "collecting the result failed: {}{}".format(error, ": " + os.fsdecode(stderr).strip() if stderr else "")
    record = {
        "repo": str(repo),
        "worktree": str(worktree),
        "base": base_sha,
        "sandbox": "danger-full-access",
        "status": result.status.value,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "error": result.error,
        "collection_error": collection_error,
        "changed_files": collected.changed_files if collected else None,
        "ignored_files": len(collected.ignored_files) if collected else None,
        "warnings": warnings,
    }
    write_evidence(out, prompt, record, result, collected)

    print("{}: {}".format(result.status.value, out))
    print("worktree: {}".format(worktree))
    if collected is not None:
        print("changed files: {}, ignored files: {}".format(len(collected.changed_files), len(collected.ignored_files)))
    for warning in warnings:
        print("warning: {}".format(warning))
    for error in (result.error, collection_error):
        if error:
            print("error: {}".format(error))
    print("remove with: git -C \"{}\" worktree remove --force \"{}\"".format(repo, worktree))
    if result.answer is not None:
        print()
        print(result.answer)
    return 0 if result.status is RunStatus.COMPLETED and not warnings and collected is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
