---
name: legacy-test-harness-setup
description: Set up a fast, repeatable development and test loop for legacy software that was not designed for automated testing, so that changes can be verified quickly and, where possible, several agents can work at the same time in separate git worktrees or branches. Surveys the codebase and its environment (databases, file shares, network services, machine-wide state), interviews the operator, designs isolation and testability changes, staffs a team of agent roles (security, testing, performance, refactoring, debugging, new development) in whatever form the current harness supports, iterates with the operator until satisfied, and finally writes a repo-local skill that documents the workflow it built. Use when tests share a database, folders, ports, or services and concurrent runs collide; when the test suite is slow, flaky, or mostly end-to-end; or when asked to make a legacy repo safe for parallel agents, including teams whose developers, CI, and product run on different operating systems.
---

# Legacy test harness setup

Legacy systems usually test end to end against shared, long-lived state: one database server, one set of folders, one FTP or HTTP endpoint, one installed service.
That works for one developer running one suite at a time.
It breaks the moment two agents in two worktrees run at once, and it makes every iteration slow.

This skill turns such a repository into one with a fast, trustworthy loop.
It fixes the environment first, by giving each concurrent run its own copy of everything that changes.
It then improves the code's testability where the operator wants it.
It ends by writing a repo-local skill that teaches every future agent the workflow.

It works in any agentic harness.
It ships no scripts, because the tooling it produces belongs to the target repository and its platform.

## Phases and gates

Run the phases in order.
Where the table names a gate, only the operator can pass it.
Passing checks do not pass a gate.

| Phase | Output | Gate |
|---|---|---|
| 0. Orient | harness and platform facts, working-record location | none |
| 1. Survey | shared-resource inventory, loop baseline, playback of your understanding | operator says "ready" |
| 2. Design | decision table per resource, testability track, staffing | operator approves the design |
| 3. Generate | tooling, config and test-fixture changes, team definitions, draft repo-local skill | none; go straight to phase 4 |
| 4. Test & adjust | evidence that the loop works, adjustments | operator says "satisfied" |
| 5. Publish | final repo-local workflow skill | operator reviews the diff |

Phases 3 and 4 form a loop.
Go back to phase 2 when testing shows that a design decision was wrong, not just its implementation.
Tell the operator when you do, and why.

### Standing rules

- **Ask before you assume.** Never design while the operator is still answering survey questions. A design built on a guess gets rejected, and the guess usually shows only when the operator corrects it.
- **Machine-wide and irreversible actions need explicit approval, each time.** These include installing database instances or services, opening ports, changing machine configuration, writing outside the repository, and dropping or overwriting any database or folder you did not create in this run. Approval for one does not cover the next.
- **Never touch the operator's existing shared environment.** The default database instance, the existing shares, and the services people use today stay as they are. Build new isolated copies next to them.
- **Verify on the real artifact.** "The script ran" is not evidence. A concurrent run that passes, a query showing untouched rows, or a timing measurement is.
- **Record measurements with their scope.** Write down the platform, tool versions, and date with every number you report.

### Platforms

The machine you run on is one platform, not necessarily the only one.
The product, each developer's machine, the CI agents, and the harness can each run a different operating system (Windows, Linux, macOS) and shell (PowerShell, cmd, bash, zsh).
The same program can also differ between them in version, edition, and behavior. For example:

- A fresh Windows machine has only Windows PowerShell 5.1. PowerShell 7 (`pwsh`) exists only where someone installed it, and behaves differently. The operator having it says nothing about teammates or CI.
- `sed`, `grep`, and `find` take different options on Linux (GNU) and macOS (BSD).
- A database engine can have different editions or features on different operating systems.

So:

1. **Ask; don't assume.** In the survey, list the platforms the product, the developers, and CI run on, with the shells and tool versions each one has. Mark each item as confirmed or assumed.
2. **Write tooling that runs on every platform in that list.** Use a runtime all of them have, such as the project's own language. Or write one entry point per platform, with identical commands and behavior. A single-platform script is right only when the operator confirmed that only one platform is involved.
3. **Name every program the tooling needs, with version and edition.** The tooling checks for each one and fails with a clear message when it is missing.
4. **Verify on each platform in the list.** A pass on one platform proves nothing about another. Record platform, shell, and tool versions with every result.

## Phase 0: Orient

1. Identify the harness you are running in and what it supports: repo-local skills, sub-agent definitions, parallel sessions, its project-instruction file. Use [references/harness-adaptation.md](references/harness-adaptation.md). Check each capability against the harness itself rather than relying on memory.
2. Identify the operating system, shell, and whether you have administrator rights. Never infer the OS release from a single compatibility field. This is only the platform you are on. The survey establishes which ones the workflow must support (see Platforms above).
3. Ask the operator where the working record for this run should live. Suggest `<repo>/.harness-setup/` and add it to `.gitignore` unless the operator wants it committed. The record holds the inventory, decisions, measurements, and the findings ledger, so a later session can resume the run.

## Phase 1: Survey

Combine read-only inspection with an interview.
Follow [references/survey.md](references/survey.md).

- Inspect first, so your questions are specific: test projects and runners, connection strings, hard-coded paths, hosts and ports, schema scripts, build outputs, service installers, CI configuration.
- Interview in rounds. Every round message has exactly this shape, with nothing after question 4:

  ```
  What I believe so far: <two to four sentences the operator can correct>
  1. <question> (a) <option> (b) <option> (c) something else
  2. <question> …
  3. <question> …
  4. <question>, or "Are we ready, or keep asking?" once the inventory looks complete
  ```

  Four is the ceiling. Move any further questions to the next round.
- Keep asking until the operator says they are ready. Never decide it yourself.
- Measure the baseline loop where it is safe: build time, the fastest test subset, a full suite run, and flakiness over repeated runs. Ask before running anything that writes to shared state.

Output: the **shared-resource inventory** (every resource two concurrent runs could both change, with how the code finds it), the **loop baseline**, and an explicit list of **unknowns**.

## Phase 2: Design

Work from the inventory, one resource at a time.
Use [references/isolation-patterns.md](references/isolation-patterns.md) for the environment and [references/testability.md](references/testability.md) for the code.

1. **Isolation.** For each shared resource, choose one pattern: unique keys in a shared store, per-worktree copy, a fixed pool of slots, a fake, or serialization. Give the reason, and say what the choice costs.
2. **Single source of truth.** Choose one untracked file or mechanism that tells a worktree which isolated environment it owns. Every runner reads it: agents, the IDE, the console, and CI.
3. **Guard rails.** Make the suite fail fast when no environment is claimed, when schema or setup is stale, and when two runs share one environment.
4. **Testability track.** List the seams, characterization tests, and test tiers that would shorten the loop, ordered by payoff. Keep this separate from isolation, so that either can ship alone.
5. **Staffing.** Choose the roles this repository needs, and how each runs in this harness. Follow [references/team.md](references/team.md). Default to few roles.
6. **Done.** Define "satisfied" mechanically with the operator, for example: "Two worktrees run the full suite at once, three times in a row, green, and the default environment is unchanged."

Present the design as a table with one row per resource and per decision.
Mark each row with the evidence it rests on: inspected, operator-stated, or assumed.
Rows marked "assumed" are the first targets in phase 4.

## Phase 3: Generate

Generate in small units, each of which ends in something you can check.

- **Spike first, by hand.** Set up one isolated environment manually, then run the suite against it. A green spike proves the inventory is complete. A red spike exposes a shared resource the survey missed. That is cheaper to learn before anything is scripted.
- **Tooling in the target repo's native language and shell.** Provisioning, claim and release, rebuild and reset, all idempotent. Apply [references/tooling-hazards.md](references/tooling-hazards.md) to every script that runs processes, uses ports, or hashes files.
- **Config and test-fixture changes**, as designed: the source-of-truth reader, the guard rails, and the parameterized endpoints.
- **Team definitions** in the harness's native form, as described in [references/team.md](references/team.md).
- **A draft repo-local skill**, started from [references/workflow-skill-template.md](references/workflow-skill-template.md) and marked as a draft. Writing it now shows where the workflow is still unclear.

## Phase 4: Test and adjust

Prove the loop against the "done" definition from phase 2.

- Run every check below on each platform from the survey's platform list, and record which platform each result came from.
- Run concurrent suites in separate worktrees, repeated, because collisions are intermittent.
- Try the guard rails on purpose: an unclaimed worktree, stale schema, and a double run in one environment.
- Check that the operator's original shared environment is untouched.
- Re-measure the loop baseline, and report the before and after numbers with their scope.
- Run the team on one real, small task, to check that the roles and handoffs work and are not just written down.

End every round, including one where every check passes, by reporting what was tested, what passed, what failed, and what you changed, and then asking the operator whether they are satisfied.
Do not start phase 5 until they say so.
If they are not satisfied, repeat phases 3 and 4.

## Phase 5: Publish

Finish the repo-local skill from [references/workflow-skill-template.md](references/workflow-skill-template.md).
Put it where the harness discovers repo-local skills, and add a pointer from the project-instruction file.
It documents the workflow that now exists: how to claim an environment, run the loop, rebuild after schema changes, add an environment, call the team, and recover from a broken environment.
Every measured number in it carries platform, versions, and date.

Show the operator the full diff of everything this run added.
Leave committing to the operator unless they ask you to commit.

## Worked example

[references/example-dotnet-sqlserver-ftp.md](references/example-dotnet-sqlserver-ftp.md) records one complete survey and design: a .NET Framework 4.8 / SQL Server / FTP system on Windows.
Read it to calibrate how specific the inventory and the design should get.
Do not copy its decisions, because they depend on that system's answers.
