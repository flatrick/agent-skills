# Agent instructions

Read `CLAUDE.md` in this directory and follow it. It is the single source of the conventions here, whichever agent you are.

Two parts of it are worth naming before you start:

**Cross-platform support.**
Every skill and script in this repository must work on Windows and on Unix — Linux and macOS alike.
Normalise line endings where authored content enters, pass artifacts through verbatim where they leave, and make sure anything you hash or record is identical on every platform for the same logical input.

**Hazards.**
`CLAUDE.md` keeps a running catalogue of the traps that have already cost someone a cycle here — shells that differ in what they export, text-mode I/O that translates silently, `splitlines()` breaking on characters that are not newlines, tests that pass for the wrong reason, process teardown, and executable resolution.
Read it before you debug something that "should work".
When a new one costs you a cycle, add it there rather than leaving it in a commit message.

Note for anyone running a proving-ground probe from `harness-driver`: this file reaches a child harness unless the runner passes `-c project_doc_max_bytes=0`, which it does. That isolation is deliberate — see `harness-driver/references/codex.md`.
