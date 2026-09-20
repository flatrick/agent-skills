# Codex

Use Codex as a frontier-model child harness for instruction probes, and as a sandboxed worker when the task genuinely needs a separate engine.

Everything below was re-verified on 2026-09-19 against `codex-cli 0.155.1` on Windows 11, authenticated with a ChatGPT login.
Re-verify after a version change.
Numbers from a different auth mode or operating system will differ.

## Proving-ground command

Use the maintained runner:

```bash
python3 "<skills-root>/harness-driver/scripts/harness_driver.py" \
  --harness codex \
  --prompt-file "/absolute/path/to/prompt.txt" \
  --cwd "/absolute/path/to/empty-cwd" \
  --timeout 180 \
  --out "/absolute/path/to/new-run-directory"
```

Pass only the runner options shown above.
The runner adds the isolation flags internally, so do not append the raw Codex flags from the next command.

The runner invokes this command shape, with the prompt written to stdin rather than passed as an argument:

```bash
codex exec --json --ephemeral --ignore-user-config --ignore-rules \
  --skip-git-repo-check -s read-only -C "<empty-cwd>" \
  -c project_doc_max_bytes=0 -c skills.bundled.enabled=false -c web_search=disabled \
  --disable apps --disable shell_tool --disable view_image \
  --disable image_generation --disable sleep_tool --disable code_mode_host \
  -
```

The trailing `-` is what makes Codex read the prompt from stdin.
`-m <model>` is inserted before it when the caller asks for a specific model.

## Always send the prompt on stdin

Never pass a probe prompt as an argument.
`shutil.which("codex")` resolves to `C:\nvm4w\nodejs\codex.CMD`, an npm shim that runs cmd.exe, then node, then `codex.exe`.
A multi-line prompt passed as an argument is silently truncated at the first newline and still exits 0, which looks like a successful run of a prompt nobody sent.
A prompt over roughly 8 KB fails with `The command line is too long.` and exit 1.

On stdin a 10 KB multi-line prompt arrives intact, including quotes, a literal `%TEMP%`, and shell metacharacters.
Verified end to end on 2026-09-19 by asking Codex to echo a payload line back through the runner.
The line `PAYLOAD: don't — café — 日本語 — åäö — "quoted" & piped | %TEMP%` came back identical.

## JSONL output and the final answer

`--json` emits a JSONL event stream on stdout.
Observed event types are `thread.started`, `turn.started`, `item.started`, `item.completed`, `turn.completed` carrying a `usage` object, and on failure a top-level `error` followed by `turn.failed` with exit 1.

Treat a run as complete only when all of these hold:

1. The process exits zero.
2. A `turn.completed` event is present.
3. No event carries an `item` whose `type` is outside `agent_message`, `reasoning`, and `error`.

The answer is the **last** `agent_message` with non-empty text before `turn.completed`.
One turn often holds several.
A run that attempted a blocked write produced the preamble `I'll try to create the file with apply_patch.` as the first `agent_message` and the real answer as the second.
Taking the first would have recorded the preamble as the result.

A tool-use item is a failed probe, not a partial answer.
`file_change` appears first as an `item.started`, so check every event that carries an `item`, not only `item.completed`.

A `turn.failed` message is itself a JSON string.
Surface it unwrapped rather than parsing it again, because its shape is the provider's, not Codex's.

## Default approval posture

`codex exec` does not write files unattended out of the box.
With no `-s` flag the banner reports `sandbox: read-only`.
Approval is `on-request` under the user's config and `never` under `--ignore-user-config`, but neither grants writes while the sandbox is read-only.

## Sandbox levels

`-s` is the per-invocation flag that grants more.
Each level below was exercised on 2026-09-19 with a live write attempt, not read from `--help`:

| `-s` level | Write inside the working directory | Write to the system temp directory | Write to the home directory |
|---|---|---|---|
| `read-only` (default) | Blocked, no file created | Not exercised | Not exercised |
| `workspace-write` | Allowed | Allowed | Blocked, no file created |
| `danger-full-access` | Allowed | Allowed | Not exercised |

The system temp directory is inside the writable set under `workspace-write`, so it is not a safe place to prove containment.
Use the home directory for that.

`--dangerously-bypass-approvals-and-sandbox` also exists.
Do not use it, and do not use `danger-full-access`, unless the user explicitly asks for that authority.

## Scoping the working directory

`-C <dir>` sets the child's working root.
Add `--skip-git-repo-check` so Codex will start outside a git repository.
`--ephemeral` keeps the run from persisting session files.

`-C` alone does not stop ambient project instructions from reaching the model.
See "Ambient instructions" below.

## Latency

A proving-ground turn takes about 4 to 7 seconds on this machine, with 12 seconds the slowest observed across roughly a dozen runs.
Through the runner, three live probes took 5.8, 5.3 and 4.4 seconds end to end.
Worker turns cost more because they load the user's config and run tools, ranging from 7 to 74 seconds.

A 180 second timeout is generous for a proving-ground probe.
Codex started faster than OMP in every run measured here, but that is a small sample and OMP's own cold start is the unpredictable one.

## Isolation flags

Measured on 2026-09-19 by one-at-a-time ablation against a tool-listing prompt, removing one flag per run and diffing the tools the model named.
The input-token count is the size of what the model sees, 8454 with the full set.
The `project_doc_max_bytes` and `code_mode_host` rows were re-confirmed independently; the token deltas come from the ablation sweep.
Each flag below changed something measurable when removed:

| Flag | Effect of removing it |
|---|---|
| `-c project_doc_max_bytes=0` | A repo `AGENTS.md` above the child cwd reaches the model |
| `-c skills.bundled.enabled=false` | The bundled skills block returns, 558 more input tokens |
| `-c web_search=disabled` | The `web__run` tool returns, 2456 more input tokens |
| `--disable apps` | Connected-app tools return, 10052 more input tokens |
| `--disable shell_tool` | `exec_command` and `write_stdin` return |
| `--disable view_image` | `view_image` returns |
| `--disable image_generation` | `image_gen__imagegen` returns |
| `--disable sleep_tool` | `clock.sleep` returns |
| `--disable code_mode_host` | No change to the tool listing, and no change to whether a write succeeds. It moves where the write fails. See below. |

`plugins`, `unified_exec`, `multi_agent`, `browser_use`, `browser_use_external`, `computer_use`, `in_app_browser`, `tool_suggest`, `skill_search`, `goals`, `personality`, `include_apply_patch_tool` and `agents.max_*` were each ablated with no measurable effect.
Do not add them back without a fresh measurement.

The flags live in `CODEX_ISOLATION_FLAGS` in `scripts/harness_driver.py`, so this table and the test assert the same list.

### What `--disable code_mode_host` actually buys

It is not what stops the write.
A live `apply_patch` attempt under `-s read-only` was blocked with no file created both with the flag and without it.
The flag only changes the failure path.
With it, the attempt fails at the tool router with `code-mode host is disabled`.
Without it, it fails at the sandbox with `writing is blocked by read-only sandbox`.

Keep it anyway, because two independent refusals are better than one, and it costs nothing in tokens.
Do not describe it as the reason writes fail.
`-s read-only` is the reason.

## Residual tool surface

The isolation flags do not produce a tool-free model.
Asked to list its callable tools with everything above disabled, the model still named `functions.exec`, `functions.wait`, `functions.request_user_input`, `functions.request_user_input_async`, `tools.apply_patch`, `tools.clock__curr_time`, and the six `collaboration.*` tools including `spawn_agent`.
None of these can be removed from the command line in this version.

This is why the parser rejects the run rather than trusting the flags.
A probe is tool-free because no tool item appeared in the stream, not because the tools were absent.
Blocked tool attempts print `ERROR codex_core::tools::router: ...` on stderr only and never appear in the JSONL.
The runner reads stderr for that line and records the run as invalid rather than completed, so an attempt the sandbox refused cannot pass as a clean probe.
A healthy probe leaves stderr empty.
The startup `error` item about code mode being unavailable arrives in the JSONL instead, which is why that item type stays allowed.

## Ambient instructions that survive

Two separate leaks, with different fixes.

**`$CODEX_HOME/AGENTS.md`, or `~/.codex/AGENTS.md`, reaches the model even under `--ignore-user-config`.**
Asked to list the second-level headings of any Codex CLI instructions document in its context, the model returned the four headings of the real file verbatim.
That run already had `-c project_doc_max_bytes=0` set, so the key that removes a project `AGENTS.md` does not touch this one.
Earlier probing on the same day tried six further config keys, including `include_instructions`, `agents_md.*`, `user_instructions` and `project_doc_fallback_filenames`, and none removed it either.
Treat it as not disableable from the command line in this version, and re-check after an upgrade.

Pointing `CODEX_HOME` at a scratch directory would remove it, but that directory also holds `auth.json` with the OAuth refresh token, so it would mean copying a live credential.
Do not do that.

The runner instead emits a warning naming the file whenever it exists, in `result.json` under `warnings` and on stderr.
Treat a probe result as contaminated by that file's contents rather than assuming a clean room.

**A repo `AGENTS.md` above the child cwd also reaches the model, and `-c project_doc_max_bytes=0` does remove it.**
Verified with a canary token in an `AGENTS.md` two directories above the child cwd.
Without the flag the model reported the token.
With it the model replied `NONE`, and the input-token count fell from 8528 to 8472.

Ask the model to report a value it can only know from the file.
A yes-or-no question that contains the canary proves nothing, because the token is then in the question.

## The model it actually runs

The JSONL stream carries no provider and no model.
Confirmed by inspecting every top-level key across a run, which yields only `item`, `thread_id`, `type` and `usage`.
So `AssistantReply.model` stays `None`, and the runner never reports the requested model as the observed one.

To find out which model ran, repeat the command without `--json` and read the banner on **stderr**:

```bash
codex exec --ephemeral --ignore-user-config --skip-git-repo-check -C "<cwd>" -
```

It prints `model:`, `provider:`, `approval:` and `sandbox:`.

`--ignore-user-config` changes which model runs.
On this machine the banner reported `gpt-5.6-terra` with the user's config and `gpt-6-astra` without it, reproducibly.
An unpinned probe therefore does not run the model the user thinks it does.
Pass `-m` when the model matters.

## Gotchas

**Decode as UTF-8 explicitly.**
Codex writes UTF-8 and reads UTF-8 on stdin.
Python's `text=True` uses the Windows locale codec, cp1252 on Python 3.14.3, and corrupts both directions.
This is not hypothetical.
A live OMP run through the old code recorded `don’t — café` as `donâ€™t â€” cafÃ©`.

**Setting `encoding="utf-8"` alone is not enough for stdin.**
`Popen` wraps stdin in a `TextIOWrapper` with `newline=None`, which rewrites every `\n` as `os.linesep`.
Sending `b"line one\nline two"` delivers `b"line one\r\nline two"`.
Call `process.stdin.reconfigure(newline="")` before writing, or the prompt is not the prompt.

**Kill the process tree, not the process.**
This one hangs.
The npm shim means `Popen` holds cmd.exe, which spawns node, which spawns `codex.exe`.
`process.terminate()` kills only cmd.exe, and the descendants keep the inherited stdout and stderr pipes open, so the `communicate()` after the kill never returns.
Use `taskkill /PID <pid> /T /F` on Windows.
The runner does this, and a Windows-only test in `tests/test_harness_driver.py` fails against the old teardown.

**Do not use `Get-Command codex` to reason about what Python will launch.**
PowerShell resolves it to `codex.ps1`, while `shutil.which` follows PATHEXT and returns `codex.CMD`.
They are different programs with different process trees.

## Worker mode

Worker mode is documented here but not automated in `harness_driver.py`.
The runner only does proving-ground runs.

The recipe is a throwaway git repository and an explicit `-C`:

```bash
work="$(mktemp -d)"
git init -q "$work"
printf '%s' "<task>" | codex exec --json -s workspace-write -C "$work" -
git -C "$work" status --short
git -C "$work" diff
```

The measured `workspace-write` boundary depended on the destination: a write to the home directory was blocked with no file created, while writes to the working directory and system temp directory were allowed.
A worktree provides a diff boundary for writes inside it, but it does not contain writes to temp because temp is inside the writable set.

### The diff may be unreadable, which defeats the point

On Windows, files Codex creates inside the sandbox are owned by `CodexSandboxOffline` and carry an ACL granting only `CodexSandboxUsers`, `SYSTEM` and `Administrators`.
The invoking user is not on it.
`git add` then fails with `error: open("hello-worker.txt"): Permission denied`, and `takeown` and `icacls` both fail as that user.
Codex's own shell inside the sandbox hit the same wall on its own `apply_patch` output.

Four approaches were measured on 2026-09-19.
Only the last one holds up.

| Approach | Result |
|---|---|
| Steer the model onto the shell tool instead of `apply_patch` | File still unreadable |
| `--disable code_mode_host` to force `apply_patch` closed | Blocks the shell tool too, so nothing is written at all |
| Have Codex run `git add -A` and `git diff --cached` itself and read the diff from `command_execution.aggregated_output` | The diff text does come back intact, but the in-sandbox `git add` hits the same ACL wall first |
| `-s danger-full-access` | File readable, `git add` clean, in 11 seconds |

So on this machine `danger-full-access` is the only route that reliably yields a reviewable diff.
That means no sandbox, so ask the user before reaching for it and prefer proving-ground mode whenever the task allows.
A worker run also costs far more than a probe, because it loads the user's config and `AGENTS.md`, and it ran to 211k input tokens in the worst case measured.
