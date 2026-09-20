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
Codex worker mode is documented but not automated.
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
