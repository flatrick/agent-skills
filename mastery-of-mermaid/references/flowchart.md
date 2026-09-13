# Flowchart

**Use for:** processes, algorithms, decision trees, control flow, deployment pipelines,
birds-eye system overviews.
**Avoid for:** a single short call chain over time (use `sequenceDiagram`),
pure schema (use `erDiagram`),
or anything where "who owns this step" matters more than sequence (use `swimlanes`,
see `swimlanes.md`).

## Core syntax

<!-- mermaid-render: id="flowchart--block1" -->
```mermaid
flowchart TD
    Start([Start]) --> Input[/User input/]
    Input --> Validate{Valid?}
    Validate -->|Yes| Process[Process data]
    Validate -->|No| Error[Show error]
    Error --> Input
    Process --> Save[(Save to DB)]
    Save --> End([End])
```
<img src="rendered/flowchart--block1.svg" alt="flowchart--block1" width=400px/>

Directions: `TD`/`TB` (top-down, default), `BT` (bottom-up), `LR` (left-right), `RL` (right-left).
`graph` is an accepted alias for `flowchart`.

## Node shapes

| Syntax | Shape | Typical use |
|---|---|---|
| `id[Text]` | Rectangle | Process step |
| `id([Text])` | Stadium/pill | Start/end |
| `id(Text)` | Rounded rectangle | Step or event |
| `id{Text}` | Rhombus | Decision |
| `id{{Text}}` | Hexagon | Preparation/condition |
| `id[[Text]]` | Subroutine (double border) | Predefined process |
| `id[(Text)]` | Cylinder | Database |
| `id((Text))` | Circle | Connector |
| `id(((Text)))` | Double circle | Terminal/stop marker |
| `id>Text]` | Asymmetric/flag | Special marker |
| `id[/Text/]` | Parallelogram | Input/output |
| `id[\Text\]` | Parallelogram (alt) | Output/input |
| `id[/Text\]` | Trapezoid | Manual operation |
| `id[\Text/]` | Trapezoid (alt) | Priority action |

Mermaid v11.3+ also supports a generic shape syntax with ~40 additional named shapes (`A@{ shape: manual-input, label: "..." }`,
`A@{ shape: doc, label: "..." }`, and more),
plus `icon` and `image` shapes for embedding icons/images in a node.
Use the classic bracket shapes above for anything portable;
reach for `@{ shape: ... }` only when a target renderer is confirmed to support v11.3+.

## Connections

| Syntax | Meaning |
|---|---|
| `A --> B` | Arrow |
| `A --- B` | Line, no arrow |
| `A -.-> B` | Dotted arrow |
| `A ==> B` | Thick arrow |
| `A ~~~ B` | Invisible link (layout hint only) |
| `A --o B` | Circle-ended edge |
| `A --x B` | Cross-ended edge |
| `A <--> B` | Bidirectional |
| `A -->|text| B` or `A -- text --> B` | Labeled arrow |

Chain multiple links on one line: `A --> B --> C`.
Fan patterns: `A --> B & C`, `A & B --> C`.
Don't overuse this for anything that needs per-edge styling;
see the "split compound edges" section in `style-standard.md`.

Extra dashes lengthen an edge across ranks: `---->` spans further than `-->`.
Same pattern applies to thick (`=`) and dotted (`.`) edges.

### Edge IDs (v11.10+)

Prepend an ID before the arrow: `A e1@--> B`.
This lets you style or animate one edge by identity instead of by definition-order index (which `linkStyle` uses).
See `style-standard.md` for the full edge-ID and palette convention this skill standardizes on.

<!-- mermaid-render: id="flowchart--block2" -->
```mermaid
flowchart LR
  A e1@==> B
  A e2@--> C
  e1@{ curve: linear }
  e2@{ curve: natural }
```
<img src="rendered/flowchart--block2.svg" alt="flowchart--block2" width=200px/>

## Subgraphs

<!-- mermaid-render: id="flowchart--block3" -->
```mermaid
flowchart TB
    A[Start]
    subgraph Processing
        B[Step 1]
        C[Step 2]
    end
    E[End]
    A --> B
    C --> E
```
<img src="rendered/flowchart--block3.svg" alt="flowchart--block3" width=300px/>

Above, `Processing` is one stage of a straight pipeline, so the edges name the nodes the flow runs through.
That is the exception, not the default.

**Default: an edge that crosses a subgraph boundary names the subgraph, not a node inside it.**
Naming the subgraph seals it into its own layout box and draws one arrow to its border.
Naming a node inside keeps the subgraph a label over nodes that still take part in the parent's layout.
Pick the endpoint for the shape you want.
`style-standard.md` has the full rule with a don't/do pair at both simple and complex size.

Give a subgraph an explicit id with `subgraph id [Title]`.
An id is required to point an edge at it:
`subgraph Process the data` makes the whole title the id, and `Ext --> Process the data` is a parse error.
Edge IDs, labels, and edge classes all work on an edge to a subgraph (`Ext e1@-->|submit job| Proc`).

Set a subgraph's own direction with `direction TB` as its first line.
Mermaid 11.16 honors that direction even when an edge crosses the boundary, and clips the crossing arrow at the box border,
so naming a node inside such a subgraph claims a target the rendered picture never shows.

`id@{ view: collapsed }` parses but is not honored by mermaid-cli 11.16 under either the `dagre` or `elk` layout;
the subgraph still renders expanded.
Don't rely on it, draw the collapsed form as a plain node instead.

## Styling

<!-- mermaid-render: id="flowchart--block4" -->
```mermaid
flowchart LR
    A[Node 1]:::warn
    B[Node 2]

    classDef warn fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#f66,stroke-width:2px
```
<img src="rendered/flowchart--block4.svg" alt="flowchart--block4" width=200px/>

- `classDef name <css props>` defines a reusable style;
  apply with `id:::name` inline or `class id1,id2 name` afterward.
  **Declare all `classDef`s before nodes and edges** (this skill's convention; also easier to scan).
- `style id <css props>` styles one node directly.
- `linkStyle N <css props>` styles the Nth edge by definition order (fragile, fallback only,
  see `style-standard.md`).
- A class named `default` applies to every unstyled node.

## Markdown labels, fontawesome icons, click events

- Markdown-formatted text in a label:
  `` id["`**bold** and _italic_`"] `` (needs double quotes + backticks).
  Auto-wraps long text; disable with `markdownAutoWrap: false` in config.
- Font Awesome icon:
  `` B["fa:fa-twitter some text"] `` (requires the FA CSS or icon pack registered on the render target).
- Click events (disabled under `securityLevel: strict`):
  `click nodeId "https://example.com" "tooltip"` or `click nodeId call callback()`.

## Common pitfalls

- **The word "end"** (all lowercase) as a node id or bare text breaks the parser.
  Capitalize it (`End`, `END`) or wrap it (`(end)`, `[end]`).
- A node id starting with lowercase `o` or `x` right before `---` can be parsed as a circle/cross edge (`A---oB`).
  Add a space or capitalize.
- Labels containing `()`, `{}`, `"`, or other punctuation need double quotes:
  `id1["This is the (text) in the box"]`.
- Comments use `%%` on their own line, and anything after `%%` on that line is ignored,
  including diagram syntax, so don't put a real link on the same line as a comment.
- External CSS selectors targeting Mermaid's rendered SVG classes don't reliably override its inline `!important` styles;
  use `classDef`/`style` instead.

## Common patterns

See `common-patterns.md` for feature-flow, bug-workflow, CI/CD, microservices,
and layered-architecture flowchart templates.
