---
name: "Argue–Measure–Stop"
description: Phase 0 — investigate a proposed change to any software before it is designed. Interleaves adversarial argument with real measurement (probes, spikes), and stops at a decision memo that the design starts from. Not tied to any planning, spec, or implementation workflow; never authors the design, a spec, a task, or production code.
category: Thinking
tags: [phase-0, adversarial, probe, spike, decision-memo, pre-design]
---

You are running **phase 0**: settling whether an idea is worth building, and into what shape.
Phase 1 is whatever comes next in the user's project: designing, specifying, and building the change.
The identity is the **argue ↔ measure interleaving**, not the arguing.

> **No premise verdict stands on argument alone when a probe could settle it.
> No measurement is formalized without its meaning being attacked.**

A red team without the measurement loop is confident vibes.
A measurement loop without the phase contract below is one more review step inside the change process this phase exists to stay out of.

**Input**: the idea.
If invoked with none, ask for one — a single question — and stop until answered.

---

## The phase contract

1. **Output is a decision memo and probe records.
   Nothing else.**
   No proposal, design doc, spec, task list, ticket, or backlog item, in whatever format the project uses.
2. **Hard stop at a human gate.**
   The session ends at *"here is the memo;
   the call is yours."* Never roll into designing or implementing the change in the same conversation — the design is a separate invocation, started from the memo, deliberately.
3. **Whatever the project uses to design and ship the change is strictly downstream and consumes exactly one thing: the memo.**
   That may be a spec workflow, a design doc, an issue, or a plain branch; this phase does not care which.
4. **Rules-light while investigating.**
   Inside phase 0 the only obligations are: do not modify the user's working tree or main branch (probes and spikes go in a scratch directory, a throwaway branch, or a worktree),
   do not fabricate a result, measure the kill conditions or record why no instrument exists,
   and write the memo.
   TDD, coverage, mutation, review rounds, and disposition machinery all begin at phase 1.

Why the contract, and not just the stance: once a phase can probe and spike,
sunk-cost gravity returns — *"we measured all this,
let's formalize"* — and phase 0 quietly becomes spec authoring.
The dead end has to hold at the artifact level, or it does not hold.

---

## The loop

Run these in order; revisit any of them freely.
**Frame** and **Investigate** are the two that cannot be skipped,
and each carries its own refusal clause below.

**1.
Frame** — with the human, before anything else.
Four things, in writing:

- the **use case** — who is stuck, on what, today;
- the **kill conditions** — two or three sentences of *"this idea dies if X"*;
- the **done-definition** — what is observably true when this is finished;
- the **measurement** — for *each* kill condition, the observation that would settle it.
  Name the probe, the fixture, the command, or the instrument.
  Not "investigate whether X"; the thing you would run.

Refuse to proceed until all four exist.
**Inability to state them is the first finding**, and it is usually the real one.
Probe the kill conditions *first* — they are where the idea is cheapest to lose.

The fourth item exists to catch, at the cheapest moment,
a question that **admits no measurement at all**.
A question about a historical record — what a finished branch cost,
whether past rounds were avoidable — has no probe surface: the only evidence is the artifacts,
so the phase silently collapses into reading and reasoning and produces a memo indistinguishable from a measured one.
If you cannot name an instrument for any kill condition, say so **here**,
and either reshape the question into one a probe can reach or decline the phase and use `/rubberduck`,
which argues honestly and never claims to have measured.

**2.
Prior art** — before any probe of your own.
Spend a bounded pass on how shipped tools and libraries in the same domain already solved this: their source, their test suites, their issue trackers, and this project's own history.
Say plainly what you found and what you could not find.

**3.
Investigate** — probes and a spike, against the kill conditions.

- A probe is the smallest runnable thing that settles one kill condition.
  If the project has a probe template or a probes directory, start from it.
  Otherwise keep each probe next to the memo, with a record of the command, the input, and the raw output.
- Probe the **real codebase or real data**, not only a synthetic fixture.
- A spike is throwaway by construction.
  It is cannibalized deliberately or deleted at phase 1 — never promoted into the implementation.

**You may not leave this step with a kill condition still `unmeasured` unless you write down why it is unmeasurable** — the instrument named at step 1 that turned out not to exist,
the fixture that cannot be built, the tool that was unavailable.
An `unmeasured` with a stated reason is a legitimate result and travels into the memo and the decision.
An `unmeasured` with no reason means the step was skipped,
and skipping it is the one failure this phase cannot survive:
everything downstream — the adversary's premises, the memo's confidence,
the human's call — is then argument wearing the grammar of evidence.

This is step 1's refusal clause applied to the step it protects.
Step 1 is guarded because a frame nobody can state is the finding;
step 3 is guarded for the same reason, one level in.

**4.
Adversary** — two dispatches, both **blind** and both **forbidden from critiquing wording**.
Hand each only the problem statement, the mechanism in ten lines, and the done-definition.
Never the memo prose, never a prior agent's verdict, never who proposed what.

- **Red team** — produce the strongest argument that this fails, *and* the strongest rival approach.
  Attack the **kill conditions and the done-definition themselves**, not only the mechanism:
  a self-serving done-definition ("done is what the spike already does") is the failure this catches.
- **Simplifier** — the smallest thing that serves the use case.
  What can we *not* build?

Where a dispatch's verdict turns on a premise a probe could settle,
go back to step 3 rather than accepting the argument.
That return edge is the whole method.

**5.
Close** — write the memo,
then **one** blind cold-context refutation pass on its *decision* (not its prose).
One pass, never rounds — a review recursion here re-creates the problem this phase exists to avoid.
Then stop and hand it to the human.

**A memo whose `## What was measured` cites no probe record and states no reason for that is not a phase-0 memo.**
Do not hand it over.
Go back to step 3,
or go back to step 1 and declare the question unmeasurable — those are the two exits;
handing it over anyway is not one of them.

---

## The memo

Path: `.agents/phase0/<topic-slug>/<YYYY-MM-DD-HHMMSS>.md`.
Create directories as needed.
One file per session,
stamp chosen once at the first write and reused — rewrite it in full each time, never append.
Write on any turn that produces a new conclusion; never defer to an explicit "end".

**One to two pages.
A memo that reaches thousands of words has failed** — it has become the corpus this phase exists to stop producing.

```markdown
# Phase 0: <topic>

## Use case
## Kill conditions        <!-- and, per condition: survived / died / unmeasured -->
## Done-definition
## Mechanism              <!-- ten lines, no more -->
## Prior art
## What was measured      <!-- probe/spike links, the raw result, what it does NOT show -->
## Measurement status     <!-- MEASURED (n probes cited) | UNMEASURED — <why no instrument exists> -->
## Alternatives rejected  <!-- each with the reason -->
## Decision               <!-- build / do not build / build this smaller thing / still unknown -->
## Open questions
```

`## Measurement status` is one line and it is mandatory.
`UNMEASURED` **caps the decision**:
the strongest call an unmeasured memo may make is *"still unknown,
and here is what would settle it"*.
It may not say build,
and it may not say do not build — an unmeasured kill condition is exactly the premise a build-or-kill verdict rests on.
Write the cap into the `## Decision` line itself rather than leaving the reader to infer it from a status two sections up.

Keep hedges and inconclusive flags verbatim — a caveat is part of the finding,
and dropping it in transcription turns an uncertain result into a confident wrong one.

---

## Status: on trial, not a gate

This command is **not** currently a required precondition for authoring a change,
and nothing enforces it.

It is promoted to a required gate once it has visibly **killed or shrunk at least one real idea**.
If every idea run through it passes,
the red team is decorative and the command is a tax — that outcome is a finding about the command,
and the right response is to change or delete it rather than to mandate it.

When it is promoted, the **mechanical change class is exempt** — renames, fixture additions,
path/namespace fixes, consolidations, doc and prompt updates.
Those have no kill conditions worth stating, and forcing the ritual there trains bypass.

**Precedence.**
If the project already has a pre-design brainstorming step, run this or that, not both.
Refining a change that already has a design is not this command's job.

---

## What this does NOT do

- Author or edit any design, spec, task, ticket, or backlog artifact.
- Run review rounds, dispositions, or a findings-ledger protocol.
  One memo is the record.
- Produce production code.
  A probe and a spike are throwaway; neither is a deliverable.
- Suggest, as a next step, that you do any of the above in this session.

`/rubberduck` is the sibling that argues and cannot measure.
This one may touch a compiler — and stops at exactly the same place.
