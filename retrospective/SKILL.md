---
name: "Process Retrospective"
description: Author a run's process retrospective — re-derive evidence, classify KEEP/FIX/WATCH, propose fixes for the operator to approve, self-review, and optionally verify claims with a cold-context pass. Writes one dated retrospective file; stops at a human gate. Repo-agnostic — uses this repo's own conventions when it has them, and sane defaults otherwise.
category: QA
tags: [retrospective, quality-playbook, process, workflow]
---

## Never write a bare count

**Do not state a count of anything** — files, call sites, tools, requirements, scenarios, findings,
capabilities — as a bare number in anything you write.
A count measures something that changes, so it is wrong from the moment that thing changes,
and a stale number reads exactly like a fresh one.
That makes it worse than saying nothing: it is confidently wrong, and the reader has no way to tell.

**Give the method instead — the command or query that yields the current number.**
"Every capability whose spec mentions `tfms` (`rg -l 'tfms' openspec/specs/*/spec.md`)" stays true;
"the 22 `tfms`-carrying capabilities" does not.
For example,
one project shipped exactly that kind of drift across four artifacts that then disagreed with each other for fifteen review rounds — treat that as an illustration of the failure mode,
not a fact about your repo.

If a number genuinely helps the reader, it is admissible **only** in this form,
with both halves mandatory:

> As of writing this, the count is 22 — re-derive it with `rg -l 'tfms' openspec/specs/*/spec.md`.

The stamp alone is still a trap:
it says the number is old without giving anyone a way to get the current one.

**A measurement from your own run is a different thing, and you should report it** — a test total,
a search's hit count, a mutation's red count.
That is evidence of what you did, not a claim about current state.
Give it the command that produced it, so a reader can tell the two apart.

A measured fact belongs in one place; every copy of it is a future lie.

Turn a completed run into an honest process retrospective: what the *supporting machinery* (rules,
skills, commands, agents, tools, harness) did well or badly, rated **KEEP / FIX / WATCH**,
with each fix proposed for the operator to approve.

This skill is self-contained: it carries its own doctrine (naming convention, rating scheme,
principles) below,
and adapts to whatever conventions the current repo already has instead of requiring any of them.
**If this repo already has its own process-retrospective doctrine document,
follow that instead of the defaults here** — this skill's built-in doctrine exists only as a fallback for repos that don't have one yet.

**Input**: optionally the run's `<suffix>` (change / umbrella / run name).
If omitted, infer it in Step 1 and confirm.

---

## Doctrine (fallback, if this repo has none of its own)

**When to write one.**
Write a retrospective only when the operator asks for one,
or after a multi-change autonomous run.
A single change, however it ended, does not trigger one.
Skip it — and say so — when neither holds,
or when the run was trivial and surfaced nothing new about the tooling or workflow.

**Naming.**
One file per retrospective: `<output-dir>/<timestamp>_<suffix>.md`,
timestamp from `date '+%Y-%m-%d_%H.%M.%S.%N_%Z'`, `<suffix>` = the change, umbrella, or run name.

**Rating scheme.**
- **KEEP** — worked; do not touch.
  Say why, with the proof.
- **FIX** — an actionable change.
  Name the concrete fix and the rule / agent / skill / script it touches;
  mark **(proposed)** / **(file a bug)**.
- **WATCH** — friction not yet worth a change.
  Note what recurrence would justify acting,
  and whether it's fixable in-repo or is a harness-level limitation.

**Propose, don't enact.**
A retrospective never edits a rule, agent, skill, command, or script.
Each FIX states the exact edit, and the operator decides.

---

## Mutation boundary — what this writes

- **The retrospective file** — exactly one, under `<output-dir>` (see Step 1 for how to pick it).
It does **not** edit rules, agents, skills, commands, or scripts:
each FIX is a proposal marked **(proposed)** in the file, and the operator approves it before anyone makes the edit.
It does **not** commit, merge, switch branches, file issues, or author spec changes.
The retrospective is normally committed alongside the run's other work — leave that to the owner or the run's own commit step,
unless explicitly asked to commit.

**Write on the run's own branch,
not on the repo's main/default branch —** unless that branch has already been merged into the default branch (see Step 1).

---

## Step 0 — Is a retrospective warranted?

Per the doctrine above (this repo's own, if it has one):
if the operator did not ask for a retrospective and the run was not a multi-change autonomous run,
**stop and say so** — no file.
Also stop if the run was trivial and surfaced nothing new about the tooling or workflow.
Otherwise proceed.

---

## Step 1 — Compute the output path and seed the file

**Pick `<output-dir>`:**
1. If this repo's own doctrine (or CLAUDE.md / project docs) names a location for process retrospectives,
   use that.
2. Otherwise, if a `retrospective/` directory (or similarly-named one, e.g. `retrospectives/`,
   `docs/retrospectives/`) already exists anywhere in the repo, use it.
3. Otherwise, default to a top-level `retrospective/` directory and create it.

**The subject slug for this retrospective is `retro-<run-branch>`.**
If this repo tracks per-run agent findings or ledgers (check for a `rules` or `docs` file describing such a convention,
e.g. an "agent findings ledger"),
read that ledger first — it is better evidence than reconstructing the run from `git log` alone.
If no such convention exists here, skip straight to `git log`.

**Confirm which checkout you are writing into.**
Identify the run branch and whether it has already landed on the repo's default branch:

```bash
git branch --show-current
git rev-parse --show-toplevel
git log <default-branch>..HEAD --oneline
```

If this repo is hosted on GitHub and the `gh` CLI is available,
you can additionally confirm merge state precisely:

```bash
gh pr list --head "<run-branch>" --state all \
  --json headRefName,baseRefName,state,mergedAt,url
```

Treat the run as merged only when one unambiguous matching PR targets the default branch,
reports the merged state, and has a non-null `mergedAt`.
Don't infer merge state from commit ancestry or ahead/behind counts alone — a squash merge or rebase can make those signals lie.
If `gh` isn't available or there's no GitHub remote, or the PR metadata is ambiguous,
ask the user whether the branch is already merged rather than guessing.

If the run has merged to the default branch,
write the retrospective there.
Otherwise write it on the run's own branch/worktree, using paths relative to that checkout.

Seed the header **immediately** via **Write** so a file exists even if the run aborts:

```markdown
# Process retrospective — <short title>

**When:** <start> → <end>
**Type:** <autonomous execution run | interactive change | bug fix | other — say which>
**Scope:** <one or two sentences on what the run did>

### What worked — KEEP
### What hurt — FIX
### Friction — WATCH
```

---

## Step 2 — Gather evidence and RE-DERIVE every count

Do not copy counts from an earlier chat message — re-derive them now from ground truth:

- **Branch commits + timestamps** — `git log <base>..HEAD` for the run's SHAs.
- **Gate results** — whatever this repo's build/lint/test/pre-commit gates are (check for a CI config,
  `package.json` scripts, a `Makefile`, or a pre-commit hook to find out what actually runs here).
- **Review findings** — any review passes that ran during the work, and their finding counts,
  up to the final clean verdict.
- **Wall-clock and friction** — long gates, sandbox/network events, interventions.

Every number that lands in the file must trace to something checked here.

---

## Step 3 — Has this friction already been watched?

A WATCH's whole contract is "note what recurrence would justify acting".
That contract needs someone to look for the recurrence, and this is the step that looks.
Run it **before** Step 4, because its purpose is to change a rating.

**Scope it to candidate WATCHes only** — not KEEPs, not FIXes.
That bounds the cost to a handful of searches per run.

For each observation you are about to rate WATCH:

1. **Search on the least-paraphrasable token** — an identifier, a filename, a command, a wire field.
   Not your own sentence, which a prior retrospective will have worded differently:

   ```bash
   rg -il '<least-paraphrasable-term>' <output-dir>/
   ```

2. **A search returning only your own file is a reason to widen, not a finding.**
   The most specific token is usually *too* narrow — a prior retrospective describing the same friction will have named it at a different altitude.
   Drop to the **concept noun both phrasings must share** and search again.
   Only after the widened search comes back empty may you write "no prior occurrence",
   and then record which patterns you tried.
3. **A hit changes the rating.**
   Friction the corpus already carries is not new friction.
   It becomes a **FIX** — naming the concrete change and the rule / command / skill / script it touches — or it stays WATCH **with an explicit stated reason it is still not worth acting on**,
   citing the prior files by name.
   Silence is not available.
4. **The graduation bar is the same item in two consecutive retrospectives.**
   When that fires, say so in the file.
5. **Every WATCH you write names the term a future search will find it by.**
   This is the load-bearing half:
   without it the step degrades into a phrasing lottery within a few runs.
6. **Record the search, not just its verdict.**
   "No prior occurrence (`rg -il '…' …`)" is checkable; "new friction" is not.

What this step is **not**:

- **Not a corpus read.**
  Searches only.
  Do not read prior retrospectives, do not summarize them.
  A step expensive enough to skip will be skipped.
- **Not an automatic upgrade.**
  The graduation and its evidence are written into the file.
  A WATCH that quietly becomes a FIX with no stated trigger is the same invisibility failure relocated.
- **Not a blocker.**
  An observation with no searchable term records that its search was inconclusive and states the pattern tried.
- **Not a place for a count.**
  Cite the files, or give the `rg` command — never "the Nth occurrence".

---

## Step 4 — Classify every observation KEEP / FIX / WATCH

Apply the rating scheme above, each observation carrying its *evidence* (a caught bug,
a prevented wrong fix, a wall-clock win), not a vibe.

---

## Step 5 — Propose the FIXes for the operator to approve

For each FIX, state the exact edit and the file it touches, and mark it **(proposed)** in the file.
Do not make the edit.
The operator approves each proposal before anyone edits a rule, agent, skill, command, or script.
A fix that needs a defect report becomes **(file a bug)**.

---

## Step 6 — Inline self-review (ALWAYS)

Read the written file with fresh eyes and fix inline:

1. **Placeholder scan** — no `TBD` / `TODO` / empty sections.
2. **Structure** — the header block and all three KEEP / FIX / WATCH sections are present and correctly used.
3. **Consistency** — every count and claim matches the Step 2 evidence; no internal contradictions.
4. **No inlined change-history** — the file states current lessons;
   it does not narrate the edits made to itself while writing it.
5. **Spelling** — if this repo gates on a spell-checker (e.g. cspell) in pre-commit or CI,
   run it and add any legitimate term it flags to the appropriate ignore list or an inline exception comment.

---

## Step 7 — Optional cold-context claim verification

**Recommended** for larger or autonomous multi-step runs;
**skippable** for small interactive changes.
If the current harness supports dispatching subagents with a fresh, isolated context,
dispatch **one such agent per claim**,
each handed a single count or assertion from the file plus the run evidence that should support it (`git log`,
gate logs, review outputs).
One agent reviewing the whole file at once is a weaker check — batching claims lets a plausible one ride along with the verified ones.
Resolve every verdict before finalizing; a refuted or unverifiable claim is a result to record,
not to quietly keep.

If the harness has no subagent-dispatch mechanism available,
skip this step and say so plainly in the handoff — a single-context self-review is not a cold review,
and should never be presented as one.

---

## Step 8 — STOP

Print the file path and a one-line KEEP / FIX / WATCH tally,
then **stop**.
Do not commit unless the owner asks.

> Retrospective written: `<output-dir>/<file>`.
> KEEP <k> / FIX <f> (all proposed, none enacted) / WATCH <w>.
> Cold-verify: <ran | skipped>.
> Recurrences: <none | the items found in prior retrospectives, and which graduated to FIX>.

The recurrence line is not decoration.
It is the only place a maintainer can see that Step 3 ran at all — a step that silently stops running looks exactly like a run with no recurrences.
