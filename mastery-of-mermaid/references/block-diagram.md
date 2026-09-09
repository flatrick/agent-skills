# Block diagram

**Use for:** system/network/electrical diagrams where you need full manual control over node position,
unlike a flowchart, Mermaid's auto-layout never moves a block diagram's shapes.
**Avoid for:** anything where automatic layout is preferable (a regular flowchart is usually less work).

## Core syntax

<!-- mermaid-render: id="block-diagram--block1" -->
```mermaid
block
  columns 3
  a["A label"] b:2 c:2 d
```
<img src="rendered/block-diagram--block1.svg" alt="block-diagram--block1" width=400px/>

- `columns N` sets how many columns the grid uses; blocks wrap to a new row after N.
- `id:N` after a block makes it span N columns; blank/no suffix means span 1.
- Blocks with no explicit columns setting flow left-to-right, wrapping automatically.
- `space` (or `space:N`) inserts an empty N-column gap for layout control.

## Composite (nested) blocks

<!-- mermaid-render: id="block-diagram--block2" -->
```mermaid
block
    block:ID
      A
      B["A wide one in the middle"]
      C
    end
```
<img src="rendered/block-diagram--block2.svg" alt="block-diagram--block2" width=600px/>

`block:ID ... end` nests a group of blocks inside a parent block,
useful for representing a server with multiple services, or any part-of hierarchy.
A single-column nested block (`columns 1`) stacks its children vertically,
effectively merging them into one tall block.

## Shapes

Block diagrams reuse the flowchart shape vocabulary: `id("rounded")`, `id(["stadium"])`,
`id[["subroutine"]]`, `id[("cylinder")]`, `id(("circle"))`, `id>"asymmetric"]`, `id{"rhombus"}`,
`id{{"hexagon"}}`, `id[/"parallelogram"/]`, `id[\"parallelogram-alt"\]`, `id((("double circle")))`.

## Block arrows and space blocks

<!-- mermaid-render: id="block-diagram--block3" -->
```mermaid
block
  blockArrowId<["Label"]>(right)
  blockArrowId2<["Label"]>(down)
```
<img src="rendered/block-diagram--block3.svg" alt="block-diagram--block3" width=300px/>

Block arrows point `right`, `left`, `up`, `down`, or diagonally (`x`, `y`,
or combined like `x, down`), useful as directional connectors between rows without a full edge.

## Connecting blocks

<!-- mermaid-render: id="block-diagram--block4" -->
```mermaid
block
  A space B
  A-- "X" -->B
```
<img src="rendered/block-diagram--block4.svg" alt="block-diagram--block4" width=200px/>

Same arrow vocabulary as flowcharts (`-->`, `--`, labeled with `-- "text" -->`).
Because block diagrams provide full position control,
a `space` is required between two blocks that need to be linked but aren't adjacent in the grid,
otherwise there's no room to draw the edge.

## Styling

`style id fill:#969,stroke:#333,stroke-width:4px` and `classDef`/`class`/`:::` all work the same as in flowcharts.

## Common pitfalls

- Forgetting a `space` between blocks you intend to connect with an edge is the most common syntax error (`A - B` is invalid;
  use `A space B` then `A --> B`).
- Column width auto-adjusts to the widest block in that column;
  a single very wide label can push the whole column wider than expected.
  Use explicit `:N` spans to compensate.
