---
name: skill-eval-loop
description: Use when evaluating or hardening an existing skill against a real agentic CLI, especially when weaker-model behavior may expose ambiguous instructions.
---

# Skill Eval Loop

You cannot tell whether a skill is clear by reading it.
You wrote it, so you already know what it means.
Run it against a model that does not, and fix what that model actually gets wrong.

**Use for:** hardening a skill aimed at weaker models, or evaluating whether an existing skill holds up.
**Avoid for:** a skill nobody has drafted yet. Write something first; this loop sharpens a draft, it does not produce one.

Calling and interpreting the harness is `harness-driver`'s job.
This skill owns repeated probes, preserved evidence, judgment, and refinement.
Claude Code is the primary supervisor.
Codex and other runtimes follow the same workflow through their native command and approval tools.

## Before the loop

**1. Get the operator's target.**
What is the skill supposed to make a model do, and for whom?
If that is not stated, ask now. Everything downstream is scored against it.

**2. Write the probe set.**
A probe is a realistic task a user would actually bring, plus the excerpt of the skill a reader would actually be looking at when they answer it.
Three to five probes is usually enough.
Aim them at decisions, not recall.
A probe that asks the model to repeat a rule tests nothing; a probe that makes it *choose* between two plausible options tests the skill.
Include at least one probe covering the thing you are least sure about.

**3. Record a baseline before changing anything.**

```bash
python3 "<skills-root>/skill-eval-loop/scripts/probe.py" \
  --context "/absolute/path/to/excerpt.md" \
  --task "<probe>" \
  --runs 3 \
  --out "/absolute/path/to/runs/00-baseline"
```

Without a baseline you cannot tell a fix from noise.
The script runs each probe several times from a cold session, because one run of a non-deterministic model is an anecdote.
Resolve the script from the loaded skill's directory, not from the current working directory.
The output directory must not exist.
The script creates an empty child working directory under the output directory unless you pass a disposable directory through `--cwd`.
On Codex, request host permission for this command when OMP needs to write its runtime state under `~/.omp`.

## The loop

**Step 1, edit.**
Apply the operator's instruction, or the refinement the last pass identified.
Change one thing at a time where you can.
Two simultaneous edits and an improved result tell you nothing about which one worked.

**Step 2, probe.**
Re-run the affected probes into a new run directory, never overwriting the baseline.
Same probes, same wording. Changing the probe and the skill together invalidates the comparison.
Read `manifest.json` for batch status, each `run-NNN/result.json` for execution status, and each `run-NNN/answer.txt` for the answer.
The command exits nonzero when a child run fails or produces no complete answer.
Exit zero means the measurement completed, not that the skill passed.

**Step 3, judge.**
Read the runs. Do not score them from exit codes.
If the skill produces an artifact (a diagram, a file, a command), **execute the artifact and inspect the result**.
A model can emit confident, well-formed, wrong output that exits 0.
Then classify each failure before fixing anything, per `references/failure-taxonomy.md`.
Only one of those categories is fixed by editing the skill.

**Step 4, gate.**
If anything needs the operator, stop and ask now, before editing.
See "When to ask" below.

**Step 5, refine or stop.**
If you changed the skill, go back to step 2 and re-verify.
A change you did not re-probe is unverified.
If a full pass produced no changes, you are done.

## When to ask the operator

**Ask** when the answer is a preference, not a fact:

- Which convention to adopt when two are defensible.
- Whether a behaviour the model produced is actually wrong, or just not what you expected.
- Scope, when fixing the finding means rewriting more than the operator asked for.
- When two fixes trade off against each other and you cannot have both.
- When the skill looks correct and the model still fails, so the honest options are "accept this model cannot do it" or "restructure the skill".

**Don't ask** when you can find out:

- Whether a syntax or command actually works. Run it.
- Whether a change helped. Re-probe it.
- Typos, dead links, contradictions within the skill.

Ask in one message, with the options and your recommendation.
Do not stack up questions across passes; raise each at the gate of the pass that found it.

## Stopping

Stop when one of these is true, and say which:

- After the last edit, every probe in the set was re-run and a complete review produced no further changes. The skill is converged against this probe set.
- Remaining failures are all classified as model limitations, not skill defects.
- The operator calls it.
- You have burned the agreed budget of passes. Report where it stands rather than continuing silently.

"All probes passed once" is not a stopping condition.
Re-run before declaring convergence, because a single clean pass can be luck.

## Traps

**Teaching to the test.**
Do not tune wording until this one model passes.
If a fix only makes sense against this harness, it is overfitting and it will make the skill worse for everyone else.
Fixes should be things you would defend to a reader who never saw the probe.

**Blaming the model.**
The common failure is a confident wrong instruction, not missing capability.
Before concluding the model is too weak, try making the instruction shorter and clearer.

**Grading the prose.**
The model sounding confident is not a pass.
Check the artifact.

**Growing the skill every pass.**
Adding text is the reflex fix and it has a cost.
A weak model handed a longer document performs worse, not better.
Prefer replacing an unclear sentence over appending a clarifying one.

## The run log

Keep `runs/LOG.md` in the eval directory, one line per pass:

```
| pass | changed | probes re-run | result | note |
```

It is what lets the operator see why the skill now says what it says, and it stops you re-litigating a fix you already tried and rejected.
