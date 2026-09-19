# OMP (Pi)

Use OMP as a local, weaker model for instruction probes and bounded delegated tasks.
Do not use it for work that needs a frontier model or a predictable cold-start time.

Everything below, including the approval-mode table, was checked on 2026-09-14 against `omp v18.1.21`.
Re-verify after a version change.

## Proving-ground command

Use the maintained runner for repeatable probes:

```bash
python3 "<skills-root>/harness-driver/scripts/harness_driver.py" \
  --harness omp \
  --prompt-file "/absolute/path/to/prompt.txt" \
  --cwd "/absolute/path/to/empty-cwd" \
  --timeout 300 \
  --out "/absolute/path/to/new-run-directory"
```

Pass only the runner options shown above.
Do not append the raw OMP flags from the next command; the runner adds them internally.

The runner invokes this command shape:

```bash
omp -p --mode=json --no-tools --no-session \
  --no-extensions --no-skills --no-rules \
  --system-prompt="Follow the user message. Answer the task directly." \
  --cwd="<empty-cwd>" "<prompt>" </dev/null
```

The flags isolate different inputs:

| Flag | Effect |
|---|---|
| `--no-tools` | Disables OMP's built-in model tools |
| `--no-extensions` | Disables extension discovery |
| `--no-skills` | Disables skill discovery and loading |
| `--no-rules` | Disables rule discovery and loading |
| `--no-session` | Prevents conversation persistence |
| `--system-prompt` | Pins a minimal system prompt so the probe measures the instructions under test, not OMP's own default agentic framing |
| `--cwd` | Starts the child in an explicit disposable directory |

These flags do not make the OMP process read-only.
OMP 18.1.21 initializes runtime state below `~/.omp` before inference, including its SQLite store and daemon client records.
A workspace-restricted Codex session must request host permission for the concrete OMP or Python runner command.
OMP's `--approval-mode` controls model tool calls and cannot grant filesystem access denied by the supervising runtime.

## Always close stdin

Close stdin on every direct invocation:

```bash
omp -p "..." </dev/null
```

Without `</dev/null`, OMP can wait indefinitely in `phase: readPipedInput` when a caller captures or redirects stdout.
The Python runners use `subprocess.DEVNULL`, so callers do not add shell redirection around those commands.

## JSONL output and model identity

`--mode=json` emits a JSONL event stream.
Observed event types include `session`, `agent_start`, `turn_start`, `message_start`, `message_update`, `message_end`, `turn_end`, and `agent_end`.

Treat a run as complete only when all of these conditions hold:

1. The process exits zero.
2. A `turn_end` event contains an assistant message with non-empty `content` entries whose `type` is `text`.
3. A later `agent_end` event has `isTerminal: true`.
4. A tool-free probe has no tool results.

Read `provider` and `model` from the assistant message instead of asking the model to identify itself.
On this machine, a successful 18.1.21 run reported provider `llama-cpp` and model `Qwen3.6-35B-A3B-IQ4-coder`.

An exit code of zero without the terminal events is an invalid result, not an empty answer.
Keep raw stdout and stderr when parsing fails.
The maintained runners store the event stream, stderr, extracted answer, and normalized result separately.

## Approval modes for worker tasks

The following was re-exercised on 2026-09-14 against `omp v18.1.21` in a throwaway git worktree:

| Flag | Observed file writes | Observed arbitrary shell |
|---|---|---|
| Default | Refused | Refused |
| `--approval-mode=write` | Allowed | Refused |
| `--approval-mode=yolo`, `--auto-approve` | Not exercised | Not exercised |

Under `write` mode, asked to both write a file and run a shell `touch`, OMP created the file through its write tool
and declined the shell call, telling the caller the bash tool call needs approval or `yolo` mode.
The approval level limits tools, not all filesystem effects.

Do not use `yolo` or `--auto-approve` unless the user explicitly requests the broader authority.
Keep the supervising runtime's approval separate from OMP's model-tool approval.

## Worker scoping

For a tool-enabled worker, use a unique throwaway git worktree and an explicit `--cwd`:

```bash
run_dir="$(mktemp -d /tmp/harness-driver.XXXXXX)"
git worktree add "$run_dir" HEAD
omp -p --cwd="$run_dir" --approval-mode=write "<task>" </dev/null
git -C "$run_dir" diff
git worktree remove "$run_dir"
```

Review and retain any wanted diff before removing the worktree.
A worktree contains relative writes and makes them reviewable, but it does not prevent the child from addressing absolute paths.
Use the supervising runtime's sandbox or permission system for that boundary.

Other relevant flags include `--add-dir`, `--tools`, and `--profile`.
Do not add them to the proving-ground runner without a measured need because each one changes the evaluation environment.

## Latency

Cold start varies.
A successful one-word response on this machine took about 13 seconds, while an earlier run remained in startup past 120 seconds.
Use a timeout of several minutes for real probes and preserve partial output when it expires.

## Current support boundary

The repository has verified OMP and Codex child adapters, both for proving-ground runs.
Claude Code and Codex can supervise either.
An OpenCode child adapter needs its own reference, output parser, approval tests, and live verification before it is added.
