# Repo conventions

## Cross-platform support

**Every skill and script in this repository must work on Windows and on Unix — Linux and macOS alike.**
This is a hard requirement, not a preference.
It covers the support scripts, their tests, and the instructions the skills themselves give a reader.

A change that works on the machine you happen to be running on is not finished.
Assume this repository is checked out on all three, by people and by agents, and that the same command on the same content must produce the same result everywhere.

Two rules carry most of the weight:

- **Normalise where authored content enters** — a file a human wrote, a task string, a context document.
- **Pass an artifact through verbatim where it leaves** — a prompt file handed to a child process is bytes to transmit, not text to reinterpret.

Anything you hash, record, or compare must come out identical on every platform for the same logical input.
A hash that changes with how the file was checked out is not a reproducibility hash, and recording it is worse than recording nothing.

## Hazards

Everything below cost someone real time, and every one of them looked fine until it didn't.

**When something here surprises you and costs you a cycle, add it to this section.**
A hazard that lives only in a commit message is a hazard the next person hits again.
Write what broke, what it looked like, and the rule that avoids it.

### Your shell is not the next person's shell

`PYTHONIOENCODING=utf-8:surrogateescape` is exported in PowerShell on this machine and unset under Git Bash.
Same machine, same interpreter, same `utf8_mode: 0`: a piped child reported `sys.stdout.encoding` as `utf-8` from one shell and `cp1252` from the other.

So a suite can be green in one terminal and red in the next, and a bug can be invisible to whoever happens to have the variable set.
Never let correctness depend on an inherited environment variable.
Pin the child environment in any test that cares about encoding — a test that passes because of an ambient variable is not passing.

### Python's text mode translates, in both directions, silently

`read_text()` turns CRLF and lone CR into LF.
`write_text()` turns LF into the platform separator, so the same call writes CRLF on Windows and LF elsewhere.
`subprocess` with `text=True` or `encoding=` wraps the child's pipes the same way, and `Popen` rewrites `\n` on stdin unless you call `reconfigure(newline="")`.

Read bytes and decode explicitly; write bytes and encode explicitly.

A piped Python stdout also falls back to the locale codec, which is not UTF-8 on Windows.
A CLI here pins its own streams rather than inheriting them.

### `splitlines()` is not "split on newlines"

It also breaks on U+2028, U+2029, form feed and several others.
JSON permits U+2028 unescaped inside a string, so `splitlines()` over a JSONL stream can cut a valid record in half and then reject both halves as malformed JSON.
Split on `"\n"`.

### A green suite can be green for the wrong reason

Both of these have happened here:

- A fake binary was not executable on Windows, so `shutil.which` found the **real** `omp` on `PATH` and the test measured whatever that binary happened to do.
- A test inherited a UTF-8 environment variable and passed without the fix it was written to prove.

Make a new test fail first, and confirm it fails for the reason you intend.
A test you never saw red is a test you have not written yet.

### Killing a process is not portable

Windows needs the whole tree, because a shim process sits between you and the real binary and its descendants keep the inherited pipes open — kill only the direct child and the drain that follows never returns.
POSIX needs `killpg`, which needs `start_new_session=True` at launch.
Both paths have to exist, and neither may be the one nobody tested.

Every drain after a kill needs its own timeout.
An unbounded one hangs in the handler written to stop things hanging.

### Windows decides what is executable, and not the way you expect

Windows resolves executables through `PATHEXT`, so an extension-less script is not executable there.
That is why the test fakes ship a `.cmd` launcher on Windows and a shebang elsewhere.
`shutil.which` and a shell's own lookup do not agree with each other, so reason about the one your code actually calls, not the one you typed.

Never hardcode a path separator, a drive letter, or `/tmp`.
Use `pathlib` and `tempfile`.

### Generating source through a shell heredoc can eat a backslash level

Writing a Python file from a heredoc has silently turned `"\\n"` into a real newline, producing a file that no longer parses.
Write the file with a file-writing tool, or substitute an explicit placeholder for the backslash inside the generating code.
Either way, check that the result parses before you run it.

### Measurements are platform-scoped

Every measured claim in a `references/*.md` file records the platform, the tool version, and the date it was taken on.
A number measured on Windows says nothing about Linux.
Stating it without that qualifier is a defect in the document, not a detail.

## Markdown line breaks

Do not wrap lines just because they're long.
Break a line at a sentence boundary — a period (`.`) — and let prose run to whatever width it runs to.

Only break early, before the sentence ends, if the line is genuinely too long and there's a `,`,
`;`, or `:` in the sentence to break at.

Don't reflow existing prose to fit an arbitrary column width;
that's what causes arbitrary mid-sentence line breaks in the first place.
