# Bayesian updating

Use this playbook when several failure mechanisms remain plausible after the first distinguishing test, or when the operator asks for Bayesian ranking of hypotheses.
Choose tests that separate plausible hypotheses.
Do not turn uncertainty into invented precision.

## Terms

A hypothesis is a testable failure mechanism.
Evidence is an observation such as a reproduced behavior, trace, metric, or log event.

The prior represents the assessment before considering the next observation.
It may already include context known at the start of the update, such as local incident rates and a deployment that preceded the symptom.

The likelihood is the probability of observing the evidence if the hypothesis is true.
The posterior is the updated assessment after considering the evidence.
Likelihood asks how expected the evidence is under a hypothesis; posterior asks how plausible the hypothesis is after seeing the evidence.

## Update rules

### Several competing hypotheses

Use this calculation when exactly one hypothesis can be true and the list covers all possible causes.
Include an `other or unknown` hypothesis for causes outside the named mechanisms.
Write probabilities as decimals, such as 0.50 for 50%.
The priors must add up to 1.

1. For each hypothesis, multiply its prior by its likelihood to get its weight.
2. Add all the weights to get the total weight.
3. Divide each hypothesis's weight by the total weight to get its posterior probability.

```text
weight = prior * likelihood
posterior probability = weight / total weight
```

Here, `*` means multiply and `/` means divide.
The posterior probabilities add up to 1, apart from rounding.
If the total weight is zero, the model cannot explain the observation.
Revisit the hypotheses and inputs before calculating an update.

### One hypothesis against all alternatives

Compare the hypothesis with the possibility that it is false.
The alternatives include other failure mechanisms, not just healthy operation.

1. Divide the prior probability that the hypothesis is true by the prior probability that it is false to get the prior odds.
2. Divide the probability of the evidence when the hypothesis is true by the probability of the evidence when it is false to get the likelihood ratio.
3. Multiply the prior odds by the likelihood ratio to get the posterior odds.
4. To convert posterior odds to a probability, divide the posterior odds by the sum of 1 and the posterior odds.

```text
posterior odds = prior odds * likelihood ratio
posterior probability = posterior odds / (1 + posterior odds)
```

For an illustrative model, suppose the prior probability is 20%, so the probability that the hypothesis is false is 80%.
The prior odds are 0.20 / 0.80 = 0.25, or 1 to 4.
Suppose the evidence has a probability of 0.60 when the hypothesis is true and 0.10 when it is false.
The likelihood ratio is 0.60 / 0.10 = 6.
The posterior odds are 0.25 * 6 = 1.5, and the posterior probability is 1.5 / 2.5 = 60%.

A likelihood ratio above 1 raises the odds, a ratio below 1 lowers them, and a ratio of 1 leaves them unchanged.
Evidence provides little support when it is about as likely with the hypothesis as without it.
How often evidence appears during healthy operation alone does not determine the update.

### Limits on numerical updates

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
