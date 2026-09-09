# Venn diagram

**Use for:** showing overlap between sets using circles (feature overlap between teams, a desirable/feasible/viable-style innovation diagram). v11.12+, `venn-beta`.
**Avoid for:** anything where a single clear answer, not a spread of overlapping categories, is the point.

## Core syntax

<!-- mermaid-render: id="venn--block1" -->
```mermaid
venn-beta
  title "Team overlap"
  set Frontend
  set Backend
  union Frontend,Backend["APIs"]
```
<img src="rendered/venn--block1.svg" alt="venn--block1" width=800px/>

- `set <id>` declares one circle; identifiers can be bare words or quoted strings.
- `union <id1>,<id2>[,...]["Label"]` declares the overlap of two or more previously-declared sets. Three-or-more-way unions render the implied pairwise overlaps automatically so the higher-arity label has a visible region.
- Bracket syntax `["Display Label"]` on a `set` keeps a short identifier while showing a longer label.

## Sizes and text nodes

<!-- mermaid-render: id="venn--block2" -->
```mermaid
venn-beta
  set A["Frontend"]:20
    text A1["React"]
  set B["Backend"]:12
  union A,B["Shared"]:3
    text AB1["OpenAPI"]
```
<img src="rendered/venn--block2.svg" alt="venn--block2" width=800px/>

A trailing `:N` on `set`/`union` sets its relative size. Indented `text id["Label"]` lines attach labels inside the most recently declared set or union.

## Styling

```
style A fill:#ff6b6b
style A,B color:#333
```

Supported properties: `fill`, `color` (text), `stroke`, `stroke-width`, `fill-opacity`.
