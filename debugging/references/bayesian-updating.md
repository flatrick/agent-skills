# Bayesian updating

Use this playbook when several failure mechanisms remain plausible after the first distinguishing test, or when the operator asks for Bayesian ranking of hypotheses.
Choose tests that separate plausible hypotheses.
Do not turn uncertainty into invented precision.

## Terms

A hypothesis, \(H\), is a testable failure mechanism.
Evidence, \(E\), is an observation such as a reproduced behavior, trace, metric, or log event.

The prior, \(P(H)\), represents the assessment before considering the next observation.
It may already include context known at the start of the update, such as local incident rates and a deployment that preceded the symptom.

The likelihood, \(P(E\mid H)\), is the probability of observing the evidence if the hypothesis is true.
The posterior, \(P(H\mid E)\), is the updated assessment after considering the evidence.

## Update rules

For mutually exclusive and collectively exhaustive hypotheses, normalize the weighted likelihoods:

\[
P(H_i\mid E)=\frac{P(E\mid H_i)P(H_i)}{\sum_j P(E\mid H_j)P(H_j)}
\]

For one hypothesis against its negation, posterior odds equal prior odds multiplied by the likelihood ratio:

\[
\frac{P(H\mid E)}{P(\neg H\mid E)}=
\frac{P(H)}{P(\neg H)}\times
\frac{P(E\mid H)}{P(E\mid \neg H)}
\]

Evidence that appears often during healthy operation has a high \(P(E\mid \neg H)\).
It provides little support when it is about as likely with the hypothesis as without it.
The likelihood ratio, not the marginal frequency alone, determines how much the evidence changes the odds.

Use numerical updates only when the inputs come from measurements, defensible historical rates, or an explicitly labeled model.
Use qualitative rankings when those inputs do not exist.
A transparent qualitative update is better than a fabricated percentage.

Do not multiply likelihood ratios for observations produced by the same underlying event unless the conditional dependencies are modeled.
Repeated log lines from one exception are usually one piece of evidence, not many independent confirmations.

## Ranking table

Keep this table current throughout the investigation:

| Hypothesis | Prior assessment | Predicted observations | Supporting evidence | Disconfirming evidence | Next test | Cost and risk | Posterior rank |
|---|---|---|---|---|---|---|---|

Label each input as `measured`, `inferred`, or `guess`.
Base the initial ranking on local incident history, component exposure, known failure rates, and changes that preceded the symptom.
Treat a recent change as a reason to test, not as proof.

Status stays `open`, `supported`, `refuted`, or `unresolved` as defined in the hypotheses and evidence playbook.
A posterior rank orders hypotheses; it does not change their status.

## Choosing a test by expected update

A useful test has different predicted outcomes under the leading hypotheses.
Prefer tests whose likely outcomes change the ranking in either direction.

Test selection also depends on operational cost.
A slightly less informative read-only trace may be better than a production restart.
A system split does not automatically remove half the probability mass.
Its value depends on how the current probability mass lies across the split and how reliably the test identifies the failing side.

State the expected update before running the test:

```text
Test:
If the result is X, H1 rises because ... and H2 falls because ...
If the result is Y, H2 rises because ... and H1 falls because ...
Risk and rollback:
```

## Qualitative updates

When probabilities are unavailable, classify each observation as strong support, weak support, neutral, weak contradiction, or strong contradiction for each hypothesis.
Explain the predicted difference that justifies the classification.

Apply these checks during every update:

- Evidence common in healthy and failing states is weak evidence.
- Correlated observations do not count as independent confirmations.
- An unexpected result may require a new hypothesis.
- A high posterior does not make a dangerous intervention safe.
- Investigation priority also depends on consequence, test cost, risk, and reversibility.

## Calculated example

A service returns HTTP 500 responses with `Timeout waiting for connection pool`.
Begin with three exclusive hypotheses for this example:

| Hypothesis | Mechanism | Prior |
|---|---|---:|
| H1 | Long transactions cause database lock waits and occupy pooled connections. | 0.50 |
| H2 | An application path leaks connections. | 0.30 |
| H3 | Another cause explains the pool exhaustion. | 0.20 |

Choose a read-only test.
Capture pool metrics, a database lock-wait snapshot, and one timed-out request trace during the same interval.
Define the evidence as many active database sessions blocked on the same lock chain.

Suppose historical measurements or an explicit model justify these likelihoods:

| Hypothesis | Likelihood of the evidence | Prior weight multiplied by likelihood |
|---|---:|---:|
| H1 | 0.80 | 0.400 |
| H2 | 0.10 | 0.030 |
| H3 | 0.05 | 0.010 |

The weights total 0.440.
Normalize each weight by that total:

| Hypothesis | Posterior |
|---|---:|
| H1 | 0.400 / 0.440 = 90.9% |
| H2 | 0.030 / 0.440 = 6.8% |
| H3 | 0.010 / 0.440 = 2.3% |

This result strongly supports H1 under the stated model.
It does not authorize terminating a query.
First inspect the transaction owner, query history, request trace, and lock chronology.
Seek a distinguishing observation, such as connection checkout duration remaining normal outside the blocked transaction path.

If the likelihood values are guesses, do not report the calculated percentages as measured confidence.
Record a qualitative update instead and explain why the lock-chain observation favors H1 over H2.

## Common reasoning failures

- Confirmation bias favors tests that can support a preferred hypothesis but cannot refute it.
- Availability bias overweights a memorable recent incident without comparing the current predictions.
- Sunk-cost bias continues a low-value investigation after new evidence favors another mechanism.
- Premature closure treats a component-level symptom as the failure mechanism.
- Incomplete hypothesis sets force unexplained probability into the listed causes.
  Include `other or unknown`.

## Sources

- [Google SRE, Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
