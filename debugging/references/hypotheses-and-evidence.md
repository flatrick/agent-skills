# Hypotheses and evidence

## Claim discipline

Keep observations separate from interpretations.
An observation is a result another investigator can re-derive.
A hypothesis explains one or more observations and makes a testable prediction.
A diagnosis identifies a supported failure mechanism and its applicable bounds.

Track at least one plausible alternative until a distinguishing test rules it out.
Include an `other or unknown` hypothesis so unexplained evidence has somewhere to go.
If causes can coexist, treat the relevant combination or causal chain as its own hypothesis instead of forcing the causes to compete.
Prefer tests whose possible outcomes change what you believe.
State each test's expected outcomes and what each would change before running it.
A test that every hypothesis predicts adds little.

Use these statuses:

- `open`: not yet tested;
- `supported`: evidence favors the claim and material alternatives have been tested;
- `refuted`: a reliable observation contradicts a required prediction;
- `unresolved`: available evidence cannot distinguish the remaining explanations.

Correlation, temporal order, and a successful workaround do not by themselves establish mechanism.
A patch experiment supports a diagnosis only when it changes the predicted variable, preserves relevant controls, and excludes another explanation such as cache invalidation or restart effects.

## Evidence sufficiency

Before calling a diagnosis supported, require:

1. The mechanism predicts the observed signature.
2. At least one observation ties the mechanism to the failing execution or state.
3. A passing comparison, counterexample, or intervention narrows the difference.
4. Material alternative hypotheses are refuted or named as limitations.
5. Another investigator can re-derive the result from the recorded procedure and context.

Do not convert missing data into certainty.
State the narrowest supported conclusion and what observation would distinguish unresolved hypotheses.

## Sources

- [Google SRE, Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Zeller, Why Programs Fail, supporting materials](https://www.debuggingbook.org/)

