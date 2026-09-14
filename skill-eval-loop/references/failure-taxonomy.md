# Classifying a probe failure

**Use for:** deciding what a bad probe result means before you change anything.
**Avoid for:** deciding whether the result is bad. Judge that against the operator's target first.

Editing the skill is the reflex response to any failure, and it is the right response to only one of these five categories.
Classify first.

## The five categories

| # | Category | The signal | What to change |
|---|---|---|---|
| 1 | Skill defect | The skill is wrong, ambiguous, missing the case, or buries it | The skill |
| 2 | Probe defect | The task was unclear or unfair, and a strong model would also stumble | The probe, then re-baseline |
| 3 | Model limitation | The instruction is correct, clear and short, and it still fails | Nothing, or restructure. Record it |
| 4 | Harness artifact | Caused by how it was invoked, not what it read | The invocation |
| 5 | Not actually wrong | Output differs from what you expected but is defensible | Nothing. Operator call |

## Telling them apart

Ask in this order. The first yes decides it.

1. **Would a careful human reader, given only that excerpt, make the same mistake?**
   Yes means category 1. This is the most useful question and the easiest to skip, because you know what you meant.
2. **Is the task itself ambiguous, or does it depend on something the excerpt never had?**
   Yes means category 2. Fix the probe and take a fresh baseline, since the old one measured a different question.
3. **Was the prompt very long, truncated, or did the model echo the input instead of answering?**
   Yes means category 4. Shorten the context to the section a reader would actually consult and re-run before concluding anything.
4. **Is the output merely different from your expectation, rather than wrong against the target?**
   Yes means category 5. Take it to the operator instead of tuning it away.
5. Otherwise it is category 3.

## Category 1, skill defect

The only category fixed by editing the skill. Sub-types, each with a different fix:

- **Wrong fact.** The skill states something untrue. Verify the correction by running it, then fix.
  Observed: a Mermaid reference claimed class-diagram styling "works the same as in flowcharts". It does not, and a weak model followed that sentence into corrupting four files.
- **Ambiguous term.** A word carries a meaning inside the skill that a reader cannot recover from context.
  Observed: "birds-eye" is an audience label in one skill, and a model reading it in a file's description could not tell whether it named a diagram type. Define the term where it is used, or stop using it where a reader meets it without the definition.
- **Missing case.** The decision the probe demanded is simply not covered. Add the rule, with the test to apply it.
- **Over-narrow rule.** A rule stated for one context that a reader will wrongly generalise.
  Observed: a styling rule correct for class diagrams, stated without saying it does not apply to flowcharts or state diagrams.
- **Buried.** The rule is present and correct, but not where the reader is looking when they need it. Move it, don't restate it.

## Category 3, model limitation

Correct, clear, short, and it still fails.
Do not add text. That is the instinct and it makes things worse, since a longer document degrades a weak model further.

In order of preference:

1. Replace the explanation with a worked example. Weak models copy patterns better than they follow prose.
2. Turn the rule into a table or a checklist.
3. Remove the decision entirely by picking a default on the reader's behalf.
4. Accept it. Record the limitation in the log, and tell the operator which model it applies to.

## Category 4, harness artifact

Common causes, all fixed at the invocation and none in the skill:

- The context was the whole skill rather than the section a reader would consult.
- Tools were enabled, so the model reached the answer by trial and error and the probe measured nothing about the instructions.
- Ambient extensions, skills, or rules were loaded and changed what the model saw.
- The session carried state from a previous run. Every probe run must be cold.
- The run hit the timeout and the partial output was read as a wrong answer.
- The supervising runtime denied OMP access to its own state files before inference.
- OMP exited zero without a complete `turn_end` and terminal `agent_end` event.
- The JSONL stream was malformed or truncated.

## Writing the finding down

For every failure you act on, record: the probe, what the model did, the category, the fix, and the re-probe result.
A finding without a re-probe result is a hypothesis.
