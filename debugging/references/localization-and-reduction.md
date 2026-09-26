# Localization and reduction

Choose the dimension that has both a passing and failing point.

## Differential debugging

Compare a failing case with the nearest relevant passing case.
Vary one controlled dimension when possible: input, version, configuration, environment, state, timing, topology, or dependency response.
Record every difference before deciding which one matters.

## Boundary search and bisection

Use binary search when the property is monotonic across an ordered space.
Use version-control bisection only when each tested revision can be built and the outcome can be classified reliably.
Mark skipped or indeterminate revisions; do not force them into pass or fail.

For runtime boundaries, place observations on both sides of a component, process, host, queue, transaction, or serialization boundary.
Move the pair inward until the value or behavior first diverges.

## Minimal reproduction

Remove unrelated setup while preserving the same failure signature, not merely any failure.
Pin versions, seeds, clocks, locale, inputs, and external responses needed for repeatability.
A minimal reproduction establishes scope; it does not by itself prove the defect mechanism.

## Delta debugging

Use systematic reduction when an input, change set, event sequence, or configuration has many independent parts.
Define a reliable outcome test with `pass`, `fail`, and `unresolved`.
Repeatedly test subsets and complements until no remaining part can be removed under the chosen granularity.

Do not claim global minimality when interactions, flaky outcomes, invalid subsets, or coarse partitions limit the search.
Record the reducer, granularity, cache policy, and final signature.

## Sources

- [Zeller and Hildebrandt, Simplifying and Isolating Failure-Inducing Input](https://www.st.cs.uni-saarland.de/publications/files/zeller-tse-2002.pdf)
- [Git documentation, git bisect](https://git-scm.com/docs/git-bisect)

