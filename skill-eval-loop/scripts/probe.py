#!/usr/bin/env python3
"""Run one instruction probe several times and preserve reproducible OMP evidence."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, Tuple


HARNESS_DRIVER_SCRIPT = (
    Path(__file__).resolve().parents[2] / "harness-driver" / "scripts" / "harness_driver.py"
)

SCHEMA_VERSION = 1


class HarnessDriverInvocationError(RuntimeError):
    """harness_driver.py itself could not be run to completion."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_prompt(context_paths: Sequence[Path], task: str) -> str:
    parts = [path.read_text(encoding="utf-8").rstrip("\n") for path in context_paths]
    parts.append(task.strip())
    return "\n\n".join(parts)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        help="Context file to include. Repeat for multiple files.",
    )
    task = parser.add_mutually_exclusive_group(required=True)
    task.add_argument("--task", help="Task text. A leading @path remains supported.")
    task.add_argument("--task-file", help="File containing the task text.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", required=True, help="New directory for this pass.")
    parser.add_argument("--harness", default="omp", choices=["omp"])
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--cwd",
        help="Disposable child cwd. Defaults to an empty directory inside --out.",
    )
    args = parser.parse_args(argv)
    if args.runs <= 0:
        parser.error("--runs must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def load_task(args: argparse.Namespace) -> Tuple[str, dict]:
    if args.task_file:
        path = Path(args.task_file).resolve()
        value = path.read_text(encoding="utf-8")
        return value, {"kind": "file", "path": str(path), "sha256": sha256_text(value)}
    if args.task.startswith("@"):
        path = Path(args.task[1:]).resolve()
        value = path.read_text(encoding="utf-8")
        return value, {"kind": "file", "path": str(path), "sha256": sha256_text(value)}
    return args.task, {"kind": "inline", "sha256": sha256_text(args.task)}


def command_template(args: argparse.Namespace, child_cwd: Path) -> list:
    template = [
        sys.executable,
        str(HARNESS_DRIVER_SCRIPT),
        "--harness",
        args.harness,
        "--prompt-file",
        "prompt.txt",
        "--cwd",
        str(child_cwd),
        "--timeout",
        str(args.timeout),
    ]
    if args.model:
        template += ["--model", args.model]
    template += ["--out", "run-NNN"]
    return template


def invoke_harness_driver(
    args: argparse.Namespace, prompt_path: Path, child_cwd: Path, run_dir: Path
) -> dict:
    command = [
        sys.executable,
        str(HARNESS_DRIVER_SCRIPT),
        "--harness",
        args.harness,
        "--prompt-file",
        str(prompt_path),
        "--cwd",
        str(child_cwd),
        "--timeout",
        str(args.timeout),
    ]
    if args.model:
        command += ["--model", args.model]
    command += ["--out", str(run_dir)]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=args.timeout + 30
        )
    except subprocess.TimeoutExpired as error:
        raise HarnessDriverInvocationError(
            "harness_driver.py did not return within {}s: {}".format(
                args.timeout + 30, " ".join(command)
            )
        ) from error
    except OSError as error:
        raise HarnessDriverInvocationError(
            "could not launch harness_driver.py: {}".format(error)
        ) from error
    if completed.returncode not in (0, 1):
        raise HarnessDriverInvocationError(
            "harness_driver.py exited {}: {}".format(
                completed.returncode, completed.stderr.strip()
            )
        )
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        raise HarnessDriverInvocationError(
            "harness_driver.py exited {} but wrote no result.json in {}".format(
                completed.returncode, run_dir
            )
        )
    return json.loads(result_path.read_text(encoding="utf-8"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.out).resolve()
    if output_dir.exists():
        print("output directory already exists: {}".format(output_dir), file=sys.stderr)
        return 2
    if not HARNESS_DRIVER_SCRIPT.is_file():
        print("required sibling script not found: {}".format(HARNESS_DRIVER_SCRIPT), file=sys.stderr)
        return 2

    try:
        contexts = tuple(Path(path).resolve(strict=True) for path in args.context)
        for path in contexts:
            if not path.is_file():
                raise OSError("context is not a file: {}".format(path))
        task, task_source = load_task(args)
        prompt = build_prompt(contexts, task)
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 2

    child_cwd = Path(args.cwd).resolve() if args.cwd else output_dir / "child-cwd"
    if args.cwd and not child_cwd.is_dir():
        print("child cwd is not a directory: {}".format(child_cwd), file=sys.stderr)
        return 2

    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print("output directory already exists: {}".format(output_dir), file=sys.stderr)
        return 2

    if not args.cwd:
        child_cwd.mkdir()

    context_records = []
    for path in contexts:
        value = path.read_text(encoding="utf-8")
        context_records.append(
            {"path": str(path), "sha256": sha256_text(value), "bytes": len(value.encode("utf-8"))}
        )
    prompt_path = output_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    request_record = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "harness": args.harness,
        "model_requested": args.model,
        "runs_requested": args.runs,
        "timeout_seconds": args.timeout,
        "child_cwd": str(child_cwd),
        "contexts": context_records,
        "task_source": task_source,
        "prompt_file": "prompt.txt",
        "prompt_sha256": sha256_text(prompt),
        "command_template": command_template(args, child_cwd),
    }
    (output_dir / "request.json").write_text(
        json.dumps(request_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    results = []
    try:
        for index in range(1, args.runs + 1):
            run_dir = output_dir / "run-{:03d}".format(index)
            result = invoke_harness_driver(args, prompt_path, child_cwd, run_dir)
            results.append(result)
            print(
                "run-{:03d}: status={} exit={} {}ms".format(
                    index, result["status"], result["exit_code"], result["duration_ms"]
                )
            )
    except HarnessDriverInvocationError as error:
        print(str(error), file=sys.stderr)
        return 3

    completed = sum(1 for result in results if result["status"] == "completed")
    result_entries = [
        {
            "run": index,
            "path": "run-{:03d}/result.json".format(index),
            "status": result["status"],
        }
        for index, result in enumerate(results, start=1)
    ]
    versions = {result["harness_version"] for result in results if result.get("harness_version")}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "harness": args.harness,
        "harness_version": next(iter(versions)) if len(versions) == 1 else None,
        "model_requested": args.model,
        "runs_requested": args.runs,
        "timeout_seconds": args.timeout,
        "child_cwd": str(child_cwd),
        "contexts": context_records,
        "task_source": task_source,
        "prompt_file": "prompt.txt",
        "prompt_sha256": sha256_text(prompt),
        "runs": result_entries,
        "completed": completed,
        "failed": len(results) - completed,
        "execution_success": completed == len(results),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "wrote {} run(s) to {}; {} execution failure(s)".format(
            len(results), output_dir, len(results) - completed
        )
    )
    print("Read the answers and inspect produced artifacts. Execution success is not a grade.")
    return 0 if completed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
