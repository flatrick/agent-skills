# Hazards for generated tooling

The provisioning, claim, reset, and fixture code that this skill generates runs processes, opens ports, writes files, and hashes content.
Every hazard below has cost real time in practice.
Most of them behave differently on Windows, Linux, and macOS, so a script that works on one platform is untested on the others.
Check generated tooling against each one that applies, on every platform from the survey's platform list.

## Programs differ between platforms

- **Don't assume a program exists, or which variant it is.** Windows ships Windows PowerShell 5.1, while `pwsh` (PowerShell 7) is a separate install. GNU and BSD `sed`/`grep`/`find` take different flags. A database client's version can differ between machines.
- **Check required programs at start-up**, print the version found, and fail with a clear message naming what to install.
- **Prefer the project's own runtime** for tooling when every platform already has it, rather than a shell that one platform lacks.

## Environment

- **Never let correctness depend on an inherited environment variable.** The same machine and interpreter can report different stdout encodings from two shells, because one exports a variable and the other doesn't. Pin what matters inside the tool.
- **A missing variable must fail loudly.** It must never select a shared default environment.

## Text and bytes

- **Text-mode I/O translates line endings silently** in both directions on some platforms. Read and write bytes, and encode explicitly, wherever content is hashed, compared, or passed through.
- **Hash normalized content.** Normalize line endings before hashing source files, so the same checkout gives the same hash on every machine.
- **Split records on `\n`, not on a generic "split lines".** Generic splitters also break on characters such as U+2028, which JSON allows inside strings.

## Processes

- **Stopping a process tree is platform-specific.** On Windows, kill the whole tree, because shims keep the inherited pipes open. On POSIX, start a new session or process group and signal that group.
- **Every wait after a kill needs its own timeout.** An unbounded drain hangs in the very handler written to stop hangs.
- **Never use `pkill -f <pattern>`.** The pattern matches the command line of the shell running `pkill`, so that shell is killed too. Signal the PID or process group you recorded at launch.
- **Windows resolves executables through `PATHEXT`.** An extension-less script isn't executable there, and different lookup functions don't agree.

## Ports and services

- **Every request to a local port needs a timeout.** A socket can accept connections and never answer, for example when a child process inherited the listener.
- **Check "something listens" and "it answers" separately.** Use a bare connect for the first and a bounded request for the second. "Connects but doesn't answer" is a state of its own.
- **Give each slot its own port range.** Don't rely on probing for a free port at the moment of launch.

## Paths

- Never hard-code a path separator, a drive letter, or a temp directory. Use the platform's path and temp-dir APIs.
- Keep machine-wide slot directories outside every worktree, so that deleting a worktree doesn't delete a slot.

## Tests of the tooling

- **Make each new test fail first, for the reason you intend.** A fake binary that isn't executable lets the real binary on `PATH` answer, and the test measures the wrong thing.
- **Pin the child environment** in any test that depends on encoding or locale.
