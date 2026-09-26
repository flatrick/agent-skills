# Investigation record and diagnosis report

## Claim record

Create one row or section for every material observation, measurement, hypothesis, diagnosis, and causal link.

| Field | Required content |
|---|---|
| ID | Stable identifier such as `OBS-003`, `HYP-002`, or `DX-001` |
| Type | Observation, measurement, hypothesis, diagnosis, or causal link |
| Status | Open, supported, refuted, or unresolved |
| Claim | One testable statement |
| Supporting evidence | Evidence IDs and why they support it |
| Contradicting evidence | Evidence IDs or `none observed` |
| Re-derivation | Exact command, query, fixture, or manual procedure |
| Context | Commit, version, environment, time window, and input |
| Result | Raw or summarized observed result |
| Interpretation | What the result changes and what it does not prove |
| Limitations | Missing data, observer effects, unsafe tests, or scope bounds |
| Provenance | Source and a corroboration path for historical or human evidence that cannot be rerun |

Keep commands cross-platform when practical.
If a procedure is platform-specific, label it and provide the corresponding procedure for other supported platforms or state the limitation.

## Diagnosis report

1. Mixed-audience summary: expected behavior, observed behavior, impact, and diagnosis status.
2. Failure mechanism: the shortest supported causal chain from defect or state to symptom.
3. Technical evidence: claim IDs, results, and context.
4. Ruled-out hypotheses: what distinguished each alternative.
5. Uncertainties and limits: unresolved explanations and applicability bounds.
6. Re-derivation: ordered commands or manual steps.
7. Handoff: either an implementation-ready defect statement, an unresolved next observation, or an offer of broader causal analysis that requires operator approval.

Do not include a patch when diagnosis discovered the cause.

## Sources

- [Google SRE, Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [HSE HSG245, Investigating accidents and incidents](https://www.hse.gov.uk/pubns/hsg245.pdf)
