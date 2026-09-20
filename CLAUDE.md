# Repo conventions

## Cross-platform support

**Every skill and script in this repository must work on Windows and on Unix — Linux and macOS alike.**
This is a hard requirement, not a preference.
It covers the support scripts, their tests, and the instructions the skills themselves give a reader.

A change that works on the machine you happen to be running on is not finished.
Assume this repository is checked out on all three, by people and by agents, and that the same command on the same content must produce the same result everywhere.

### Text I/O is the trap that keeps catching us

Python's text mode is platform-dependent in both directions, silently.
`read_text()` translates CRLF and lone CR to LF.
`write_text()` translates LF to the platform separator, so the same call writes CRLF on Windows and LF elsewhere.
`subprocess` with `text=True` or `encoding=` wraps the child's pipes the same way, and `Popen` rewrites `\n` on stdin unless you call `reconfigure(newline="")`.

So:

- Read bytes and decode explicitly; write bytes and encode explicitly.
- **Normalise line endings where authored content enters** — a file a human wrote, a task string, a context document.
- **Pass an artifact through verbatim where it leaves** — a prompt file handed to a child process is bytes to transmit, not text to reinterpret.
- Anything you hash, record, or compare must come out identical on every platform for the same logical input.
  A hash that changes with how the file was checked out is not a reproducibility hash, and recording it is worse than recording nothing.

### Processes, paths, and executables

Killing a process is not portable.
Windows needs the whole tree, because a shim process sits between you and the real binary and its descendants keep the inherited pipes open.
POSIX needs `killpg`, which needs `start_new_session=True` at launch.
Both paths have to exist, and neither may be the one nobody tested.

Never hardcode a path separator, a drive letter, or `/tmp`.
Use `pathlib` and `tempfile`.

Windows resolves executables through `PATHEXT`, so an extension-less script is not executable there.
That is why the test fakes ship a `.cmd` launcher on Windows and a shebang elsewhere.
`shutil.which` and a shell's own lookup do not agree with each other, so reason about the one your code actually calls.

### Tests

Tests run on both platforms.
If a test can only be meaningful on one, skip it explicitly and say why, rather than letting it quietly pass.
Never let a test fall through to a real binary on `PATH` because its fake was not executable on that platform — a green suite that shelled out to the real thing is worse than a red one.

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
