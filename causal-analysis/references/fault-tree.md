# Fault-tree analysis

Use a fault tree to enumerate explicit combinations of lower-level events or conditions that can produce one top outcome.

Start with a precisely defined top event.
Decompose it through gates:

- `OR`: any input is sufficient for the parent event under the stated model;
- `AND`: all inputs are required for the parent event under the stated model.

Give every event and gate a stable ID.
State assumptions about independence, timing, common-cause failures, and scope.
Continue until leaves are supported basic events, bounded undeveloped events, or explicitly unresolved hypotheses.

A tree expresses a model of possible production paths.
Validate branches against event evidence before using it as an account of what occurred.
Do not infer probability without defensible input probabilities and a model that handles dependencies.

## Sources

- [NASA Fault Tree Handbook with Aerospace Applications](https://ntrs.nasa.gov/citations/20020065844)
- [NASA NPR 8621.1, Appendix I-3 analytical techniques](https://nodis3.gsfc.nasa.gov/displayAll.cfm?Internal_ID=N_PR_8621_0001_&page_name=ALL)

