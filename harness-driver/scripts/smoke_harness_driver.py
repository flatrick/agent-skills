#!/usr/bin/env python3
"""Run the Codex and OMP proving-ground smoke probes in one fresh directory."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_PROMPT = "Reply with exactly OK."
DEFAULT_EXPECTED_ANSWER = "OK"
HARNESS_DRIVER = Path(__file__).with_name("harness_driver.py")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--expect-answer", default=DEFAULT_EXPECTED_ANSWER)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out-root", help="Existing directory that will contain the new run.")
    parser.add_argument(
        "--require-clean-context",
        action="store_true",
        help="Reject a probe that reports ambient-context warnings.",
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root_parent = Path(args.out_root).resolve() if args.out_root else None
    if root_parent is not None and not root_parent.is_dir():
        print("output root is not a directory: {}".format(root_parent), file=sys.stderr)
        return 2
    root = Path(tempfile.mkdtemp(prefix="harness-driver-smoke-", dir=root_parent))
    exit_code = 0
    for harness in ("codex", "omp"):
        child_cwd = root / "{}-cwd".format(harness)
        child_cwd.mkdir()
        command = [
            sys.executable,
            str(HARNESS_DRIVER),
            "--harness",
            harness,
            "--prompt",
            args.prompt,
            "--expect-answer",
            args.expect_answer,
            "--cwd",
            str(child_cwd),
            "--timeout",
            str(args.timeout),
            "--out",
            str(root / "{}-evidence".format(harness)),
        ]
        if args.require_clean_context:
            command.append("--require-clean-context")
        exit_code = max(exit_code, subprocess.run(command).returncode)
    print("evidence: {}".format(root))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
