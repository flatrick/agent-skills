# Runtime evidence

Use the least intrusive source that can distinguish the active hypotheses.
Preserve raw artifacts and analyze copies.

## Evidence sources

- Stack traces locate active call paths, exception propagation, and blocked threads.
  Preserve all threads for deadlocks and stalls.
- Structured logs establish event fields and local order.
  Check sampling, buffering, clock source, rotation, and correlation IDs before inferring absence or global order.
- Distributed traces show cross-boundary latency and parent-child relationships.
  Missing spans can mean instrumentation gaps rather than missing work.
- Debuggers and watchpoints reveal control flow and the first mutation of a value.
  Account for timing changes caused by breakpoints.
- Assertions test an invariant close to its first violation.
  A late assertion identifies detection, not necessarily origin.
- Dumps preserve process state after crashes, hangs, or resource exhaustion.
  Record symbols, executable build identity, and capture settings.
- Profilers measure where time or allocation accumulates.
  Match sampling mode and duration to the workload.

Tie every capture to the exact version, environment, time window, input, and command or manual procedure.
Record tool-induced changes such as disabled optimization, attached debugger, extra logging, or sampling overhead.

## Sources

- [Google SRE, Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Microsoft, Collecting user-mode dumps](https://learn.microsoft.com/windows/win32/wer/collecting-user-mode-dumps)

