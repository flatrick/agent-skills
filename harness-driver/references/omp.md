# omp (Pi)

**Use for:** a local, cheap, genuinely weak model to test instructions against, and for one-shot delegated tasks.
**Avoid for:** work needing a frontier model, or anything where a slow cold start matters.

Everything below was verified by running it on 2026-09-14, against `omp v18.1.19`.
Re-verify if the version has moved.

## The model it runs

```
omp -p --no-tools "Reply with only the exact name of the model answering this, nothing else." </dev/null
```

On this machine that returns `llama-cpp/Qwen3.6-35B-A3B-IQ4-coder`, a local llama.cpp-served MoE with roughly 3B active parameters at IQ4 quantization.
That is a fair weak-model proxy, not a toy.
It has decent baseline knowledge and follows clear instructions well; it goes wrong when an instruction is confidently misleading, not when it is merely terse.
In `--mode=json` the `provider` and `model` fields on every assistant message carry the same answer without spending a turn.

## Always close stdin

```
omp -p "..." </dev/null
```

**Without `</dev/null` it can hang forever in `phase: readPipedInput`.**
This bites when stdout is redirected to a file, which is exactly what you do when capturing output.
It does not always reproduce, which makes it worse, not better.
Close stdin on every invocation and the problem goes away.

## Proving ground, no side effects

```
omp -p --no-tools "<the instructions under test>

<the task>" </dev/null
```

`--no-tools` disables every built-in tool, so the run cannot touch anything.
This is the default mode for testing instructions.
Feed it the actual text a reader would have, then read what it produces.

## Machine-readable output

`--mode=json` emits a JSONL event stream, not a single JSON document.
Event types seen: `session`, `agent_start`, `turn_start`, `message_start`, `message_update`, `message_end`, `turn_end`, `agent_end`.

The final answer is on the last `turn_end` event, in `message.content[]`, in the entries with `type == "text"`.
Note that `content[]` also carries `thinking` entries, so filtering on type matters.

```python
import json
final = None
for line in open(path):
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("type") == "turn_end":
        final = event["message"]
print("".join(c["text"] for c in final["content"] if c["type"] == "text"))
```

Plain text mode prints a `Working...` line before the answer, so strip it when parsing without `--mode=json`.

## Approval, what each level actually permits

The default is safe.
Out of the box `omp -p` **refuses to write**, and says so in prose rather than failing, which means an unwary caller reads a polite explanation and a zero exit code instead of a result.

| Flag | File writes | Arbitrary shell |
|---|---|---|
| *(default)* | refused | refused |
| `--approval-mode=write` | allowed | refused |
| `--approval-mode=yolo`, `--auto-approve` | allowed | allowed |

`--approval-mode=write` is the setting to reach for when a task needs to produce files.
Verified: it wrote `proof.txt`, and it declined to run a shell command.

One subtlety worth knowing.
Asked to `touch` a file under `write` mode, the model reported that bash was blocked and then created the file anyway through the write tool.
So `write` bounds *which tool* it may use, not *what effects* it can achieve on the filesystem.
Scope the directory, do not rely on tool choice to limit blast radius.

`yolo` and `--auto-approve` were not exercised here.
Do not reach for either without the user explicitly asking.

## Scoping

- `--cwd=<dir>` sets the working directory. Verified: writes land there.
- `--add-dir=<dir>` adds a workspace directory beyond the working one, repeatable.
- `--tools=<a,b>` restricts which built-in tools are enabled.
- `--profile=<name>` isolates auth, sessions, settings and caches from the user's interactive use.
- `--no-session` keeps the run ephemeral.

For any run with writes enabled, combine a throwaway git worktree with `--cwd`:

```
git worktree add /tmp/hd-run HEAD
omp -p --cwd /tmp/hd-run --approval-mode=write "<task>" </dev/null
git -C /tmp/hd-run diff        # review before anything is kept
git worktree remove /tmp/hd-run --force
```

## Latency

Cold start is slow and variable.
One run sat in startup past 120 seconds.
Budget generously, several minutes for a tool-using task, and run it in the background rather than blocking on it.

## Other flags worth knowing

`--model=<fuzzy>` picks the engine, `--smol`/`--slow`/`--plan` set role models, `-c`/`--continue` and `-r`/`--resume` carry a session forward, `--system-prompt` and `--append-system-prompt` shape the run.
These come from `omp --help` and were not individually exercised.
