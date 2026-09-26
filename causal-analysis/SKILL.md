---
name: causal-analysis
description: Analyze causal factors behind consequential, recurring, systemic, organizational, human-factor, control, or non-software outcomes. Use for causal analysis, root-cause analysis, RCA, incident analysis, timelines, Ishikawa or fishbone analysis, fault trees, causal diagrams, and opt-in Mermaid visualization. Do not use for ordinary software debugging or defect localization. When debugging raises a broader causal question, require an explicit operator-approved handoff before starting.
---

# Causal analysis

Explain why an undesired outcome occurred well enough to support a decision.
Use plural causal factors unless the evidence establishes a single sufficient cause.

If debugging exposed a broader question about recurrence, controls, organization, consequences, or human factors, begin only after the operator explicitly approves this handoff.
Direct requests for causal analysis or non-software investigations need no debugging precondition.

## Set the analysis boundary

Define the undesired outcome, affected parties, time and system scope, evidence cutoff, and the decision the analysis must support.
Preserve applicable legal, safety, labor, privacy, and incident-response constraints.

For analysis likely to span several experiments, sessions, evidence sources, or consequential decisions, ask whether the record should stay inline, use temporary storage, or use permanent storage.
If storage is requested, ask for the exact path and wait for the answer before writing an analysis file.
Do not choose a path or lifetime.

For regulated or safety-critical conclusions, use the required investigation protocol and qualified domain experts.
This skill does not replace those authorities.

## Build claims from evidence

1. Build a factual timeline before asserting causal order.
   Mark estimated time, conflicting accounts, and clock uncertainty.
2. Classify each claim as a trigger, proximate cause, contributing factor, condition, failed control, or unresolved hypothesis.
   Do not force every fact into a causal role.
3. Select a method based on the question, not on a preferred diagram.
4. Test each causal link against supporting and contradicting evidence, counterexamples, alternative explanations, and safe counterfactual tests.
5. Treat human actions in the context of available information, workload, interface, training, incentives, supervision, and organizational constraints.
   Preserve individual accountability where the evidence supports it, but do not use "human error" as a terminal explanation.
6. Map each proposed corrective action to supported claim IDs.
   State the mechanism it changes and a re-runnable effectiveness check.

Read [Evidence and causal claims](references/evidence-and-causal-claims.md) for claim standards and [Analysis records and reports](references/record-and-report.md) for traceability and reporting.

## Choose a method

| Question | Method |
|---|---|
| Is there a narrow causal chain to examine? | [Five Whys](references/five-whys.md) |
| Which candidate factors should the team organize and test? | [Ishikawa or fishbone](references/ishikawa.md) |
| What meaningful difference separates good from bad or before from after? | [Change analysis](references/change-analysis.md) |
| Which control was missing, failed, bypassed, or ineffective? | [Barrier analysis](references/barrier-analysis.md) |
| How did events and conditions interact over time? | [Event-and-causal-factor charting](references/event-and-causal-factor.md) |
| Which explicit AND/OR combinations can produce the outcome? | [Fault-tree analysis](references/fault-tree.md) |

Methods can complement one another, but each added method must answer a distinct question.
Do not mistake a categorized candidate, earlier event, tree branch, or repeated "why" for a proven cause.

## Report and stop

Lead with a mixed-audience summary.
Then give the factual timeline, supported causal factors and failed controls, technical evidence, alternatives ruled out, uncertainties, re-derivation instructions, proposed corrective actions mapped to claim IDs, and effectiveness checks.

Stop before implementing actions, assigning owners, setting due dates, tracking closure, or declaring effectiveness unless the operator separately authorizes that work.

## Optional Mermaid visualization

Visualization is opt-in.
If a timeline, Ishikawa, causal flowchart, or fault tree would materially clarify timing, state, boundaries, or interacting factors, offer one specific diagram and the reader question it would answer.
Do not generate it until the operator agrees.
Do not repeat a declined offer unless the analysis changes materially.

When opted in, use [Mermaid visualization templates](references/visualization.md).
Every node or entry must include a stable claim or hypothesis ID from the analysis record.
Ishikawa category bones are the one exception: they group claims and carry no ID.
