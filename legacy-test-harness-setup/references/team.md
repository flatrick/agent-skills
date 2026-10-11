# Staffing the team

A team member is a **role**: a focused brief, a set of permissions, and a defined output.
How a role runs depends on what the harness supports (see [harness-adaptation.md](harness-adaptation.md)).

## Role catalog

Staff a role only when the survey shows work for it.
Start with the fewest roles that cover the design, and add one when a real task needs it.

| Role | Staff when | Writes code? | Output |
|---|---|---|---|
| **Developer** (new development) | always: it is the only role that changes product code | yes, in its own worktree | commits on a branch |
| **Test engineer** | always for this skill: it owns tiers, characterization tests, fixtures, and guard rails | yes, test code and test tooling, in its own worktree | tests, plus the evidence that they fail without the change |
| **Debugger** | there is a flaky suite, intermittent collisions, or unexplained failures | no, only disposable probes | diagnosis: mechanism, evidence, alternatives ruled out |
| **Refactorer** | the testability track has seams to add | yes, behavior-preserving changes only | commits guarded by characterization tests |
| **Security reviewer** | the setup touches credentials, connection strings, shares, ports, or service accounts, or the product handles sensitive data | no | findings |
| **Performance reviewer** | loop time is a stated goal, or resources are tight (instances per machine, memory caps) | no | measurements and findings |

Adapt the briefs to the repository.
Name its languages, its test framework, its slot tooling, and the commands for its fast tier.
A brief that could apply to any repository is too vague.

## Rules that keep a team from going wrong

These come from analyzing a standing multi-session team.
Every one of them prevents a known failure.

1. **Fresh context per task by default.** A long-lived role session drifts as its context fills and is compacted. Spawn a sub-agent per task when the harness supports it. Use a standing session only for a stated reason: the operator wants to watch or steer that role directly, or it needs a different model, permissions, or tools.
2. **Each writer has its own worktree.** Two writers never share one, but writers in different worktrees work at the same time. Reviewers work read-only, on a **commit**, not a live working tree, and every finding cites the commit.
3. **Findings, not commands.** A reviewer reports what is wrong and how to re-derive it. Only the developer, or the orchestrator, decides what to change. A role that reads untrusted content (dependencies, fixtures, issue text) must never be able to issue instructions to a writer.
4. **Only findings with evidence block.** A blocking finding comes with a way to re-derive it: a failing test, a command, a query. Everything else is advisory. It gets logged, and it never forces another round. Keep a legitimate category for "cannot be reproduced cheaply" (races, environment-only defects), so that reviewers don't go blind to them.
5. **"Done" is mechanical.** It is a list of checks a script or the operator can run, defined in phase 2. A role's opinion that work is done is not done.
6. **Bounded rounds.** Set a round cap, and escalate to the operator when the same finding is reopened. An LLM deciding when to stop is not a kill condition.
7. **A ledger, not messages.** Durable state goes in a findings file in the working record, with id, commit, role, severity, evidence, status, and ruling. Messages between roles carry only pointers to it. A rejected finding stays rejected unless new evidence arrives.
8. **Verify the artifact, not the report.** A reviewer checking "does it work" runs it. Reading the developer's summary doesn't count.

## Mapping roles onto concurrency

Any role that **runs the suite** needs a slot while it runs.
That includes every writer, the debugger whenever it reproduces a failure, and the performance reviewer whenever it measures.
A role that only reads a commit needs no slot.
So the number of slots caps how many roles can run the suite at once, not the size of the team.
State that cap in the published workflow skill.

## Checking the team in phase 4

Run one small, real task through the team before calling the setup done.
Check that roles received the context they needed, that findings reached the ledger with evidence, and that no two suite runs shared a slot.
Then check that the task finished within the round cap.
Fix the briefs where a role guessed.
