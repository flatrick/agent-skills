# Quadrant chart

**Use for:** four-quadrant prioritization or analysis (effort vs. impact, reach vs. engagement).
**Avoid for:** exact routing logic,
or when a single clear answer is the point (a quadrant chart implies a spread of options).

## Core syntax

<!-- mermaid-render: id="quadrant-chart--block1" -->
```mermaid
quadrantChart
    title Feature backlog: effort vs. impact
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Major projects
    quadrant-2 Quick wins
    quadrant-3 Fill-ins
    quadrant-4 Thankless tasks
    Bulk export: [0.3, 0.6]
    Dark mode: [0.45, 0.23]
```
<img src="rendered/quadrant-chart--block1.svg" alt="quadrant-chart--block1" width=500px/>

- `x-axis <left> --> <right>` and `y-axis <bottom> --> <top>` label the axes;
  the right/top half of the label is optional (`x-axis Urgent` alone labels only the left end).
- `quadrant-1` through `quadrant-4` label the four regions: 1 = top-right, 2 = top-left,
  3 = bottom-left, 4 = bottom-right.
- Points are `"label": [x, y]` with x and y each in `0`-`1`.

## Point styling

Direct: `Point A: [0.9, 0.0] radius: 12` (also `color`, `stroke-width`, `stroke-color`).
Class-based:
define with `classDef class1 color: #109060, radius: 10` and apply with `Point A:::class1: [0.9, 0.0]`.
Precedence is direct style > class style > theme.

## Configuration and theming

`config.quadrantChart` controls `chartWidth`/`chartHeight`, padding,
and font sizes for axis/quadrant/point text.
Theme variables `quadrant1Fill`-`quadrant4Fill` and `quadrant1TextFill`-`quadrant4TextFill` set per-quadrant background/text colors;
`quadrantPointFill`/`quadrantPointTextFill` style points.

## Common pitfalls

- If no points are given, axis and quadrant text render centered in each quadrant;
  adding points shifts axis labels to the chart edges.
