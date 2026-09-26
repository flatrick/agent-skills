---
name: harness-driver
description: Use when testing instructions against another agentic CLI or delegating a bounded task to an external CLI harness.
---

# Harness Driver

Another agent CLI on this machine is a tool you can call, not a colleague you can trust.
This skill covers how to call one and what you owe the user afterwards.

Claude Code is the primary supervising runtime for this skill.
Codex runs the same commands through its shell tool and requests host permission for writes outside its sandbox.
OpenCode, Pi, and other supervisors use their equivalent command and approval tools.
The harness's approval mode never overrides the supervising runtime's permissions.

**Use for:** testing whether instructions survive a weaker reader, getting a genuinely independent second attempt at a task, or running work in an engine this session does not have.
**Avoid for:** anything you can do directly and verify faster yourself.
Shelling out to another agent costs latency, tokens, and a verification pass, so it has to buy something a local edit does not.

## Pick the job first

Two jobs, different rules. Decide which before you invoke anything.

| Job | What it is | Tools | Success looks like |
|---|---|---|---|
| **Proving ground** | You wrote instructions for weaker models. Run them through a weak model and watch it fail. | Disable tools and ambient instruction discovery | You learn where the instructions are unclear |
| **Worker** | You want a task done, in an isolated place, by another engine. | Scoped, in a throwaway worktree | You get a diff you then verify yourself |

**Proving ground is the default.**
It disables model tools and removes ambient instructions, but the harness process can still write its own runtime state.
It is the only way to find out what an instruction actually says to someone who does not already know what it means.
Reach for worker mode only when the work genuinely needs a separate engine.

## Repeatable smoke check

Run `python3 "<skills-root>/harness-driver/scripts/smoke_harness_driver.py"` to start Codex and OMP sequentially in fresh empty directories.
It requires the exact answer `OK` and prints the retained evidence directory.
Use `--require-clean-context` only when a Codex home `AGENTS.md` warning must invalidate the probe.

## Read-only review handoff

To have Codex review a repository, write the request to a prompt file and hand over the file, not an inline script:

`python3 "<skills-root>/harness-driver/scripts/codex_review.py" --prompt-file <file> --worktree <git-worktree> --label <what>`

It runs `codex exec -s read-only` with the prompt on stdin and Codex's shell tool enabled, so Codex can read the tree and cannot write it.
It passes `--ignore-user-config`, because a user config that auto-approves escalation requests lets a blocked command re-run outside the sandbox.
So the user's configured model does not apply; pass `--model` to choose one.
On Windows it adds `-c windows.sandbox="elevated"`, without which the read-only sandbox rejects every command, reads included.
Before launching, it asks each Python it can reach (its own interpreter, and `python` and `python3` on `PATH`) which interpreter it really runs.
It puts a short note with those full paths, versions and how to call one ahead of the prompt on stdin, because a bare `python` may be a launcher the sandbox cannot start.
The task decides which interpreter to use.
`prompt.txt` holds the prompt file unchanged, and `stdin.txt` holds exactly what Codex received.
Evidence (`prompt.txt`, `events.jsonl`, `stderr.txt`, `answer.txt`, `result.json`) goes to the main checkout's `.scratch/<worktree-name>/codex/<label>-<timestamp>/`, or `.scratch/codex/` from the main checkout itself; `--out` overrides it.
It prints the evidence directory and Codex's final answer, and exits non-zero unless the run completed.
Write the prompt file inside the supervising session's own worktree: a worktree-isolated Claude Code session refuses both inline heredocs and `Write` calls into the main checkout.
Its tests are `harness-driver/tests/test_codex_review.py`.

## Worker handoff

To have Codex write code, write the task to a prompt file and run:

`python3 "<skills-root>/harness-driver/scripts/codex_worker.py" --prompt-file <file> --repo <git-worktree> --label <what> --unsandboxed`

It creates a detached throwaway worktree under the main checkout's `.worktrees/`, from `--base` (default `HEAD`), and runs `codex exec -s danger-full-access` there.
`danger-full-access` means no sandbox: on Windows the `workspace-write` sandbox leaves files the user cannot read (see `references/codex.md`).
So the script refuses to run without `--unsandboxed`, and you pass that only when the user has agreed to an unsandboxed worker.
It stages everything and diffs against the base, so `patch.diff` includes commits Codex made.
`git add -A` skips ignored files, so the ones Codex created are listed in `ignored.txt` instead.
If any modified, untracked or ignored file in the supervising worktree changes size or mtime during the run, the result gets a warning and the exit code is non-zero.
So write nothing into the supervising worktree while a worker runs.
If collecting the diff fails after the run, `result.json` records `collection_error` and the rest of the evidence is still written.
Evidence (`prompt.txt`, `events.jsonl`, `stderr.txt`, `answer.txt`, `patch.diff`, `status.txt`, `ignored.txt`, `result.json`) goes where the review handoff puts it.
`patch.diff` holds the staged bytes exactly, including CRLF and non-UTF-8 content.
The worktree stays in place so you can build and test it; the script prints the command that removes it.
Pass `--no-project-docs` to keep repository `AGENTS.md` files out of Codex's context.
Its tests are `harness-driver/tests/test_codex_worker.py`.

## Test suite

Run `python3 -m unittest -v harness-driver/tests/test_harness_driver.py` before changing the runner.
On Windows 11 with Python 3.14.3, this suite ran 39 tests in 74.258 seconds on 2026-09-20 because it exercises timeout and process-tree teardown paths.
Allow at least 90 seconds and capture the final summary rather than relying on partial dot output.

**Feed it the section, not the whole skill.**
A weak model handed a long document will echo it back instead of acting on it.
Measured on 2026-09-14 against OMP's then-configured `Qwen3.6-35B-A3B-IQ4-coder`: given one reference file plus a task, `omp` answered correctly; given that file concatenated with its parent `SKILL.md`, the same model regurgitated the input and never reached the task.
So test the excerpt a reader would actually be looking at when they make the decision.
If the excerpt alone is not enough to get the answer right, that is the finding, and the fix is in the document, not the prompt.

## Non-negotiables

**Never trust the harness's own report.**
It will tell you it succeeded. Verify the artifact it produced, not the summary it wrote.
An exit code of 0 means the process ended, not that the work is right.

**Never point a tool-enabled harness at a real working tree.**
Give it a throwaway git worktree so relative writes arrive as a reviewable diff.
For OMP the worktree is only a diff boundary, not an operating-system sandbox, and it does not prevent absolute-path writes.
Codex under `-s workspace-write` has a destination-based boundary: the measured home-directory write was blocked, while writes to the workspace and system temp directory were allowed.
Check `references/codex.md` before relying on that boundary.

**Escalate approval per invocation, never globally.**
Every harness here has a per-run flag for this. Editing the harness's global config to grant permissions changes the user's environment behind their back, and it persists after you are done.

**Tell the user you delegated.**
Name the harness and the model, and say how you verified the result.

## When the result is bad

A weak model producing a bad answer in proving-ground mode is a finding, not a failure.
Fix the instructions, then re-run the same prompt and see whether the output changed.
Do not conclude "the model is too weak" until you have tried making the instructions clearer and shorter.
The failure is usually a confident wrong instruction, not missing capability.

## Verified child harnesses

| Harness | Binary | Reference |
|---|---|---|
| omp (Pi) | `omp` | `references/omp.md` |
| Codex | `codex` | `references/codex.md` |
| OpenCode | `opencode` | Not implemented as a child harness |

OMP and Codex have executable adapters in this repository, both for proving-ground runs.
Codex worker mode is automated by `scripts/codex_worker.py`.
Claude Code, Codex, OpenCode, and Pi can supervise either adapter when they can run Python and the child binary.
Check the binary exists (`command -v <name>`) before planning around it.
Availability differs per machine.

## Adding a harness

Write `references/<name>.md` covering these, and **verify every one by running it**, not by reading `--help`:

1. The one-shot non-interactive invocation, with a working example.
2. How to get machine-readable output, and how to extract the final answer from it.
3. What the default approval posture is. Does it write files unattended out of the box?
4. The per-invocation flag that grants more, and exactly what each level permits.
5. How to scope the working directory.
6. Startup and run latency, so callers set a sane timeout.
7. Gotchas that cost you time. Especially anything that hangs.
8. The model it actually runs, and how to ask it.

Record the date and version you verified against.
Harness CLIs change fast, and a stale recipe here is worse than none because it reads as checked.
