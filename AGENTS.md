# Agent instructions

Read `CLAUDE.md` in this directory and follow it. It is the single source of the conventions here, whichever agent you are.

The one that is most often broken, so it is repeated here:

**Every skill and script in this repository must work on Windows and on Unix — Linux and macOS alike.**
Text-mode file and pipe I/O is platform-dependent in both directions and is the usual cause.
Normalise line endings where authored content enters, pass artifacts through verbatim where they leave, and make sure anything you hash or record is identical on every platform for the same logical input.
See "Cross-platform support" in `CLAUDE.md` for the rest, including process teardown, executable resolution, and how measured claims must be scoped.

Note for anyone running a proving-ground probe from `harness-driver`: this file reaches a child harness unless the runner passes `-c project_doc_max_bytes=0`, which it does. That isolation is deliberate — see `harness-driver/references/codex.md`.
