---
name: debugging
description: Diagnose and localize software or system failures through evidence-driven debugging, troubleshooting, reproduction, runtime behavior, and differential tests. Use for unexplained failures and requests to investigate or visualize a failure with an opt-in Mermaid timeline. Also use for bug-fix requests whose defect is not yet evidenced, to challenge the premise and recommend diagnosis before any fix. Do not use to implement a fix whose defect and mechanism are already established.
---

# Debugging

Establish what fails, where it fails, and why.
Stop after an evidence-backed diagnosis if this investigation discovers the cause.
Do not implement that fix unless the operator separately authorizes implementation.

## Start with the evidence gate

Before opening a new investigation, ask whether the alleged defect already has enough evidence to act on.

A known bug passes when the available evidence identifies all of these:

- the violated expectation and the observed result;
- a reproducible case or bounded production observation;
- the defect location or failure mechanism;
- a credible link from that mechanism to the observation;
- the environment, version, and input to which the claim applies.

If it passes, state why and return to the already-authorized implementation workflow.
Do not repeat diagnosis merely because this skill was selected.

If it does not pass and the operator asked for a fix, stop before investigating or editing anything.
Tell the operator that the reported behavior is not yet established as a defect, and name the gate items the available evidence does not satisfy.
Recommend diagnosing the failure first, and begin only after the operator agrees.
A fix request is not permission to investigate.

If the operator asked for a diagnosis or investigation, investigate.
Do not treat an issue label, prior guess, correlation, or proposed patch as proof.

## Preserve evidence and scope

Record the earliest available logs, traces, dumps, inputs, timestamps, versions, configuration, topology, and state before a test or restart destroys them.
Separate expected behavior, observed behavior, impact, and the smallest known failure boundary.

For an investigation likely to span several experiments, sessions, evidence sources, or consequential decisions, ask whether the record should stay inline, use temporary storage, or use permanent storage.
If storage is requested, ask for the exact path and wait for the answer before writing an investigation file.
Never choose the path or lifetime yourself.

Use the claim schema and report format in [references/record-and-report.md](references/record-and-report.md).

## Investigate

1. Reproduce the failure under controlled conditions.
   If reproduction is unsafe, destructive, too costly, or impossible, establish precise bounds from preserved evidence and state why a live reproduction was not attempted.
2. Write competing hypotheses.
   For each one, name a predicted observation that distinguishes it from at least one alternative.
3. Choose the cheapest safe high-information test.
   Seek disconfirming evidence as deliberately as confirming evidence.
4. Use disposable or ignored probes.
   Do not modify tracked product files during diagnosis.
   If instrumentation must touch tracked files, stop and request separate authorization.
5. Narrow the failing region across input, code, time, topology, configuration, state, or dependency boundaries.
6. Repeat until the evidence supports a failure mechanism, refutes material alternatives, or reaches an explicit unresolved boundary.

Read only the playbooks needed for the failure:

- [Hypotheses and evidence](references/hypotheses-and-evidence.md) for claim strength, competing explanations, and evidence sufficiency.
- [Localization and reduction](references/localization-and-reduction.md) for differential debugging, boundary search, bisection, minimal reproduction, and delta debugging.
- [Runtime evidence](references/runtime-evidence.md) for debuggers, stacks, logs, traces, profilers, dumps, assertions, and watchpoints.
- [Flaky and concurrent failures](references/flaky-and-concurrent.md) for intermittent, timing, scheduling, race, and ordering failures.
- [Performance and resources](references/performance-and-resources.md) for latency, throughput, CPU, memory, file descriptors, connection pools, and saturation.
- [Distributed and production systems](references/distributed-and-production.md) for partial failure, queues, retries, clocks, consistency, and high-risk environments.
- [Build, environment, and state](references/build-environment-and-state.md) for toolchains, dependencies, configuration, caches, schemas, migrations, and data state.

## Conclude

Lead with a mixed-audience diagnosis.
Then give the failure mechanism, supporting evidence, alternatives ruled out, uncertainties, scope, and exact re-derivation instructions.
An unresolved result is valid when the evidence does not distinguish the remaining hypotheses.

When the investigation discovers the cause, stop before editing product code.
State the smallest supported implementation handoff and the evidence that justifies it.

If the evidence raises recurring, systemic, consequential, organizational, human-factor, or failed-control questions, offer broader causal analysis and say what decision it could support.
Do not begin it without explicit operator approval.
Ordinary defect localization does not need that handoff.

## Optional visualization

Do not produce a diagram unless the operator opts in.
If timing, runtime behavior, state, boundaries, or interacting factors would become materially clearer, offer one specific Mermaid visualization and state the reader question it would answer.
Do not repeat a declined offer unless the investigation changes materially.
