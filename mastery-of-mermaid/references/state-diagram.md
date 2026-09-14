# State diagram

**Use for:** state machines, record lifecycles,
status transitions (`stateDiagram-v2` is the current, actively-developed syntax;
prefer it over the legacy `stateDiagram`).
**Avoid for:** continuous polling loops (use a sequence diagram) or a process where "who does this step" matters more than which state something is in (use `swimlanes.md`).

## Core syntax

<!-- mermaid-render: id="state-diagram--block1" -->
```mermaid
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
```
<img src="rendered/state-diagram--block1.svg" alt="state-diagram--block1" width=200px/>

`[*]` is the special start/end pseudostate;
the direction of the arrow to/from it determines whether it's a start or an end.
A transition can carry a label: `s1 --> s2 : A transition`.
A state gets a description either via `state "Description" as s2` or `s2 : Description`.

## Composite (nested) states

<!-- mermaid-render: id="state-diagram--block2" -->
```mermaid
stateDiagram-v2
    [*] --> First
    state First {
        [*] --> second
        second --> [*]
    }
    [*] --> NamedComposite
    NamedComposite: Another Composite
    state NamedComposite {
        [*] --> namedSimple
        namedSimple --> [*]
    }
```
<img src="rendered/state-diagram--block2.svg" alt="state-diagram--block2" width=400px/>

Nesting can go arbitrarily deep.
Transitions between composite states are allowed at the outer level;
transitions between internal states of *different* composite states are not.

## Choice, fork, join

<!-- mermaid-render: id="state-diagram--block3" -->
```mermaid
stateDiagram-v2
    state if_state <<choice>>
    [*] --> IsPositive
    IsPositive --> if_state
    if_state --> False: if n < 0
    if_state --> True : if n >= 0

    state fork_state <<fork>>
    [*] --> fork_state
    fork_state --> State2
    fork_state --> State3
    state join_state <<join>>
    State2 --> join_state
    State3 --> join_state
    join_state --> State4
```
<img src="rendered/state-diagram--block3.svg" alt="state-diagram--block3" width=500px/>

## Concurrency

Within a composite state, separate parallel regions with `--`:

<!-- mermaid-render: id="state-diagram--block4" -->
```mermaid
stateDiagram-v2
    [*] --> Active
    state Active {
        [*] --> NumLockOff
        NumLockOff --> NumLockOn : EvNumLockPressed
        --
        [*] --> CapsLockOff
        CapsLockOff --> CapsLockOn : EvCapsLockPressed
    }
```
<img src="rendered/state-diagram--block4.svg" alt="state-diagram--block4" width=400px/>

## Notes, direction, comments

<!-- mermaid-render: id="state-diagram--block5" -->
```mermaid
stateDiagram-v2
    direction LR
    State1: The state with a note
    note right of State1
        Important information
    end note
    State1 --> State2
    note left of State2 : Shorter note form
    %% this is a comment
```
<img src="rendered/state-diagram--block5.svg" alt="state-diagram--block5" width=400px/>

`direction` (`TB`/`LR`/etc.) sets layout,
including per-composite-state via a nested `direction` line.

## Styling

<!-- mermaid-render: id="state-diagram--block6" -->
```mermaid
stateDiagram-v2
    classDef movement font-style:italic
    classDef badBadEvent fill:#f00,color:white,font-weight:bold

    [*] --> Still
    Still --> Moving
    Moving --> Crash

    class Moving, Crash movement
    Crash:::badBadEvent
```
<img src="rendered/state-diagram--block6.svg" alt="state-diagram--block6" width=100px/>

Two ways to apply a `classDef`: the `class` statement (works for start/end states too),
or the `:::` shorthand at the point of use.
**Limitation:** `classDef` styling cannot be applied to or within composite states themselves.

## Common pitfalls

- Spaces in a state's name require defining it with a bare id first (`stateId: Description with spaces`),
  then referencing the id.
- Transitions can't cross between internal states of two different composite states;
  route the transition through the composite states themselves.
- The legacy `stateDiagram` (without `-v2`) still works but has fewer features;
  use `stateDiagram-v2` for new diagrams.
- **A note must name a defined state, never a transition label.**
  `note right of Foo` where `Foo` is the text after a transition's `:` parses cleanly and then dies at layout with `Error: No such shape: undefined`,
  which names neither the note nor the offending target.
  Check that every note target also appears on the left or right of a `-->`.

## Common patterns

See `common-patterns.md` for order-lifecycle and user-account-state templates.
