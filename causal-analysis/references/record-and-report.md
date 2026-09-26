# Analysis records and reports

## Claim record

Create one row or section for each material observation, measurement, causal link, diagnosis, and action-effectiveness claim.

| Field | Required content |
|---|---|
| ID | Stable identifier such as `EVT-004`, `CF-002`, `CTRL-003`, or `ACT-001` |
| Type | Observation, measurement, trigger, proximate cause, contributing factor, condition, failed control, unresolved hypothesis, or action-effectiveness claim |
| Status | Open, supported, refuted, or unresolved |
| Claim | One testable statement |
| Supporting evidence | Evidence IDs and why they support it |
| Contradicting evidence | Evidence IDs or `none observed` |
| Re-derivation | Exact command, query, fixture, or manual procedure |
| Context | Commit, version, environment, time window, and input |
| Result | Raw or summarized observed result |
| Interpretation | What the result supports and what it does not prove |
| Limitations | Missing data, uncertainty, observer effects, unsafe tests, or scope bounds |
| Provenance | Source and corroboration path for historical or human evidence that cannot be rerun |

Corrective actions also record the supported claim IDs they address, the mechanism they change, the expected observable result, and a re-runnable effectiveness check.

## Report structure

1. Mixed-audience summary: outcome, effect, scope, confidence, and decision supported.
2. Factual timeline: sourced events, conditions, gaps, and clock uncertainty.
3. Supported causal account: triggers, proximate causes, contributing factors, and failed controls with claim IDs.
4. Evidence and alternatives: supporting results, counterexamples, and ruled-out hypotheses.
5. Human and organizational context: information, workload, interface, incentives, controls, and accountability.
6. Uncertainties: unresolved claims, missing evidence, and applicability bounds.
7. Re-derivation: exact procedures and provenance paths.
8. Proposed actions: claim mapping, expected mechanism, and effectiveness checks.
9. Handoff boundary: state that implementation, ownership, dates, and closure need separate authorization.

## Sources

- [NASA NID 8621-5, Root Cause Analysis](https://nodis3.gsfc.nasa.gov/OPD_Docs/NID_8621_5.pdf)
- [HSE HSG245, Investigating accidents and incidents](https://www.hse.gov.uk/pubns/hsg245.pdf)

