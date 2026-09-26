# Opt-in Mermaid visualization

Use these templates only after the operator opts in.
State the reader question before the diagram.
Replace example text with claims from the analysis record and retain the stable IDs in every node or entry.
Ishikawa category bones are the one exception: they group claims and carry no ID.

The complete template set targets Mermaid 11.16 or newer.
The `ishikawa-beta` template requires Mermaid 11.12.3 or newer and remains experimental, so its syntax may change.
Validate against the target renderer.
A diagram represents recorded claims; it does not add evidence or prove causation.

## Chronological timeline

Reader question: What happened in what order, and where is timing uncertain?

```mermaid
timeline
    title [OUT-001] Chronology of the undesired outcome
    09h00 : [EVT-001] Supported event
    09h05 : [EVT-002] Supported event
    09h05-09h12 : [HYP-001] Ordering unresolved
    09h12 : [OUT-001] Undesired outcome
```

## Ishikawa candidate-factor map

Reader question: Which candidate and supported factors require comparison across categories?

```mermaid
ishikawa-beta
    [OUT-001] Undesired outcome
    Process
        [CF-001] Supported contributing factor
        [HYP-001] Candidate, not yet supported
    Controls
        [CTRL-001] Failed control
    Environment
        [COND-001] Relevant condition
```

Keep the map legible:

- Keep category labels to one or two short words.
  In these renders, some neighbouring category labels of 15 to 32 characters overlapped; none of 14 characters or fewer did.
- Keep consecutive factor labels on the same category from both running long.
  Long labels wrap into more lines than the layout leaves room for and print over the next factor.
  Pairs whose first label ran 66 to 69 characters, claim ID included, overprinted; pairs led by labels of 57 characters or fewer rendered cleanly.
  Shorten the earlier label of a colliding pair.
- A larger output size does not fix an overlap, because it enlarges the finished layout.
  Shorten the labels instead.
- Render the diagram and inspect it before sharing it.

These layout limits were observed with Mermaid CLI 11.16.0 and 12.0.0 on Windows 11 Home build 26200 on 2026-09-26.

## Evidence-backed causal flowchart

Reader question: Which supported links connect conditions and events to the outcome?

```mermaid
flowchart LR
    classDef supported fill:#e8f5e9,stroke:#2e7d32,color:#1b1b1b
    classDef unresolved fill:#fff8e1,stroke:#f9a825,color:#1b1b1b
    C1["[COND-001] Supported condition"]:::supported
    E1["[EVT-001] Supported event"]:::supported
    H1["[HYP-001] Alternative link unresolved"]:::unresolved
    O1["[OUT-001] Undesired outcome"]:::supported
    C1 -->|"[CL-001] supported"| E1
    E1 -->|"[CL-002] supported"| O1
    H1 -.->|"[CL-003] unresolved"| O1
```

## Fault tree with explicit gates

Reader question: Which AND/OR combinations can produce the top outcome under the stated model?

```mermaid
flowchart TB
    classDef event fill:#e3f2fd,stroke:#1565c0,color:#1b1b1b
    classDef gate fill:#f3e5f5,stroke:#7b1fa2,color:#1b1b1b
    TOP["[OUT-001] Top outcome"]:::event
    OR1{{"[GATE-001] OR"}}:::gate
    AND1{{"[GATE-002] AND"}}:::gate
    E1["[EVT-001] Basic event"]:::event
    E2["[EVT-002] Basic event"]:::event
    E3["[EVT-003] Basic event"]:::event
    OR1 --> TOP
    E1 --> OR1
    AND1 --> OR1
    E2 --> AND1
    E3 --> AND1
```

## Sources

- [Mermaid, Timeline diagram syntax](https://mermaid.js.org/syntax/timeline.html)
- [Mermaid, Ishikawa diagram syntax](https://mermaid.js.org/syntax/ishikawa)
- [Mermaid, Flowchart syntax](https://mermaid.js.org/syntax/flowchart.html)
