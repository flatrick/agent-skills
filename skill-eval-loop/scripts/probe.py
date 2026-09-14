#!/usr/bin/env python3
"""Run one probe against a harness several times, from a cold session each time, and save the output.

A single run from a non-deterministic model is an anecdote. This runs the same probe N times so a
verdict rests on how often the behaviour appears, not on whichever run you happened to see first.

    python3 scripts/probe.py --context ../mastery-of-mermaid/references/flowchart.md \\
                             --task "Draw X." --runs 3 --out runs/baseline

Each run is written to <out>/run-N.txt with the exact prompt alongside it in <out>/prompt.txt, so a
later run can be compared against an earlier one and the comparison is reproducible.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

# Tools stay off. A probe measures what the instructions make a model say, and a tool-using run
# can reach the right answer by trial and error, which is not what is being measured.
HARNESSES: dict[str, list[str]] = {
    "omp": ["omp", "-p", "--no-tools", "--no-session"],
}


def build_prompt(context_paths: list[str], task: str) -> str:
    """Assemble the prompt a reader would actually be looking at, then the task."""
    parts = []
    for path in context_paths:
        with open(path, encoding="utf-8") as fh:
            parts.append(fh.read().rstrip("\n"))
    parts.append(task.strip())
    return "\n\n".join(parts)


def run_once(harness: str, prompt: str, timeout: int, model: str | None) -> tuple[int, str]:
    """One cold invocation. Returns (exit code, combined output)."""
    cmd = list(HARNESSES[harness])
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    try:
        # stdin must be closed: omp can hang in readPipedInput when stdout is redirected.
        with open(os.devnull) as devnull:
            proc = subprocess.run(
                cmd, stdin=devnull, capture_output=True, text=True, timeout=timeout
            )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out.replace("Working...\n", "", 1).strip()
    except subprocess.TimeoutExpired:
        return 124, f"(timed out after {timeout}s)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", action="append", default=[],
                        help="File whose contents the model should see, repeatable. "
                             "Pass the excerpt a reader would actually consult, not the whole skill.")
    parser.add_argument("--task", required=True,
                        help="The task text, or @path to read it from a file.")
    parser.add_argument("--runs", type=int, default=3, help="How many cold runs (default 3).")
    parser.add_argument("--out", required=True, help="Directory to write prompt.txt and run-N.txt.")
    parser.add_argument("--harness", default="omp", choices=sorted(HARNESSES))
    parser.add_argument("--model", default=None, help="Override the harness's default model.")
    parser.add_argument("--timeout", type=int, default=300, help="Per-run timeout in seconds.")
    args = parser.parse_args()

    task = args.task
    if task.startswith("@"):
        with open(task[1:], encoding="utf-8") as fh:
            task = fh.read()

    missing = [p for p in args.context if not os.path.exists(p)]
    if missing:
        sys.exit(f"context file(s) not found: {', '.join(missing)}")

    prompt = build_prompt(args.context, task)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "prompt.txt"), "w", encoding="utf-8") as fh:
        fh.write(prompt)

    print(f"harness={args.harness} runs={args.runs} prompt={len(prompt)} chars -> {args.out}")
    failures = 0
    for i in range(1, args.runs + 1):
        started = time.time()
        code, out = run_once(args.harness, prompt, args.timeout, args.model)
        path = os.path.join(args.out, f"run-{i}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        if code != 0:
            failures += 1
        print(f"  run-{i}: exit={code} {time.time() - started:.0f}s {len(out)} chars")

    print(f"wrote {args.runs} run(s) to {args.out}; {failures} non-zero exit(s)")
    print("Read the runs. Do not score them from exit codes.")


if __name__ == "__main__":
    main()
