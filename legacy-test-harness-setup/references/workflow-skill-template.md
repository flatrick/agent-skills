# Template: the repo-local workflow skill

Phase 3 starts this file as a draft, and phase 5 finishes it.
It describes the workflow that **now exists** in the repository, not the process that built it.
A future agent reads it cold, with no access to this run's conversation.

Replace everything in angle brackets.
Delete any section that doesn't apply, rather than leaving it empty.
Follow the harness's skill format for the frontmatter.

```markdown
---
name: <repo>-test-loop
description: How to build, test, and work concurrently in <repo>. Use before running any tests, when creating a worktree, after pulling schema changes, when a test run reports a slot or schema error, and when delegating work to the team roles.
---

# <Repo> test loop

<Two sentences: what is isolated, and why it matters.
Example: each worktree leases a slot with its own SQL Server instance and FTP server, so concurrent runs can't change each other's data.>

## Platforms

| Platform | Used by | Shell | Required programs (version, edition) | Verified on (date) |
|---|---|---|---|---|
| <e.g. Windows 11 24H2> | <developers, CI> | <PowerShell 7.4> | <SQL Server 2022 Developer, …> | <date> |

<If commands differ between platforms, give each command per platform in the tables below.
If only one platform is supported, say so and say why, so nobody assumes it was an oversight.>

## Before your first test run in a worktree

<exact claim command>, then <exact rebuild command>.
The suite refuses to run without a claimed slot.
Never point it at the default environment.

## The loop

| Need | Command | Typical time (<platform>, <versions>, <date>) |
|---|---|---|
| fast tier | <command> | <time> |
| tests for one area | <command with filter> | <time> |
| full suite | <command> | <time> |

## When the suite stops you

| Message | Meaning | Do |
|---|---|---|
| <no slot claimed> | <…> | <claim command> |
| <schema hash mismatch> | the branch's schema changed since the slot was built | <rebuild command> |
| <slot busy> | another run holds this slot | wait, or check <status command> |

## Slots

<How many exist, what each contains, and what varies between them.
How to list, release, and reclaim a stale lease.
How to add a slot, and what it costs.
How to rebuild a broken slot from nothing.>
At most <N> suite runs (writers, reproductions, measurements) can happen at once, one per slot.

## Team

<One line per staffed role: what it does, when to use it, whether it writes code, and where its definition lives.
The rules: reviewers read a commit and report findings with evidence to <ledger path>; only evidence-backed findings block; at most <N> rounds before escalating to a human.>

## Testability conventions

<Test tiers and how to tag a test.
Where characterization tests live.
The seam patterns this codebase uses, with one example path each.>

## Known hazards

<Anything that cost time during setup and could cost it again, with the rule that avoids it.>
```
