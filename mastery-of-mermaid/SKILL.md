---
name: mastery-of-mermaid
description: Guide for creating, editing, and validating Mermaid diagrams of every kind (flowcharts, sequence, class, state, ER, C4/architecture, Gantt, and 25+ other types). Use whenever a user asks to diagram, visualize, map out, or document a process, system, schema, architecture, or timeline as a Mermaid diagram, or to create/update an existing .mmd file or mermaid code block. Harness agnostic - written for any AI coding assistant (Claude Code, Codex, Cursor, Pi, OpenCode, etc.), not tied to one vendor's tools.
---

# Mastery of Mermaid

Mermaid renders diagrams from plain text, so diagrams stay version-controllable, diffable,
and easy to update alongside code.
This skill covers the full workflow: pick the right diagram type, write correct syntax,
validate it, and style it consistently.

## Core workflow

1. **Understand the request.**
   Identify the diagram type, the entities and relationships involved,
   and whether you are creating new, editing an existing diagram,
   or generating one from source code.
2. **Pick the diagram type.**
   Use the selection table below.
   When two types both fit,
   prefer the simpler one (a sequence diagram over a flowchart for a short linear call chain,
   for instance).
3. **State the audience.**
   Before drawing,
   decide whether the diagram is birds-eye (a plain-language overview for stakeholders) or technical (exact service/table/function names for implementers).
   See `references/style-standard.md` for the full birds-eye vs. technical distinction.
   One document can hold both, as two separate diagrams.
4. **Generate syntactically correct Mermaid code.**
   Open `references/<type>.md` and follow it.
   Don't write syntax from memory; the per-type files carry the shapes, arrows,
   and pitfalls that a recalled example usually gets wrong.
   Use meaningful node IDs and labels,
   and apply the styling conventions in `references/style-standard.md`.
5. **Save to a file.**
   Write the diagram to a `.mmd` file (or a fenced ```` ```mermaid ```` block inside a markdown file) with a meaningful kebab-case filename, e.g. `user-authentication-flow.mmd`.
6. **Validate.**
   If you have shell access and the Mermaid CLI (`mmdc`,
   from the `@mermaid-js/mermaid-cli` npm package) is available, validate with:
   ```
   mmdc -i <filename>.mmd
   ```
`mmdc` is a plain command-line tool, not tied to any particular agent or harness,
so this step works the same way regardless of which coding assistant is running it.
See `references/cli-usage.md` for install options (global, local, npx, Docker), useful flags,
and troubleshooting.
If you don't have shell access, or `mmdc` isn't installed, and a JavaScript runtime is available,
`mermaid.parse()` is a code-only validation fallback, see `references/configuration.md`.
If neither is available,
sanity-check the syntax by eye against the relevant `references/*.md` file,
and say plainly that the diagram is unverified.
Don't claim a diagram "renders correctly" without having actually rendered it.
7. **Auto-correct errors.**
   Read the `mmdc` error message, find the line and issue, apply the fix (common causes:
   unquoted labels with spaces or special characters, wrong arrow syntax,
   a stray `end`/`o`/`x` at the start of a node id colliding with flowchart syntax,
   malformed node definitions), and re-validate.
   Repeat until it passes;
   only report a failure to the user after repeated attempts don't resolve it.
8. **Render on request only.**
   Don't render an image unless the user asks for a preview.
   Default output format is SVG:
   ```
   mmdc -i <filename>.mmd -o <filename>.svg
   ```
PNG (`-o <filename>.png`) and PDF (`-o <filename>.pdf`) are also supported.

## Diagram type selection

| Need to show | Type | Reference |
|---|---|---|
| Process, algorithm, decision tree, user flow | Flowchart | `references/flowchart.md` |
| Interactions over time (API calls, auth flows, message passing) | Sequence diagram | `references/sequence-diagram.md` |
| Object-oriented design, domain model, class relationships | Class diagram | `references/class-diagram.md` |
| State machine, lifecycle, status transitions | State diagram | `references/state-diagram.md` |
| Database schema, table relationships | Entity relationship diagram (ERD) | `references/erd.md` |
| Software architecture at any level (context, container, component, deployment) | C4 diagram | `references/c4.md` |
| Project timeline, task scheduling | Gantt chart | `references/gantt.md` |
| Proportions, distribution of a whole | Pie chart | `references/pie-chart.md` |
| Hierarchical brainstorm, knowledge map | Mindmap | `references/mindmap.md` |
| Chronology of events or milestones | Timeline | `references/timeline.md` |
| Git branching/merging strategy | Git graph | `references/gitgraph.md` |
| Four-quadrant prioritization/analysis | Quadrant chart | `references/quadrant-chart.md` |
| Requirements traceability (SysML-style) | Requirement diagram | `references/requirement-diagram.md` |
| Flow/volume between categories (energy, funds, traffic) | Sankey diagram | `references/sankey.md` |
| Line/bar chart of two numeric axes | XY chart | `references/xy-chart.md` |
| System components and modules with explicit positions | Block diagram | `references/block-diagram.md` |
| Cloud/infrastructure topology, CI/CD deployments | Architecture diagram | `references/architecture-diagram.md` |
| Network packet / byte-level layout | Packet diagram | `references/packet-diagram.md` |
| Task board across workflow stages | Kanban | `references/kanban.md` |
| Multi-dimensional comparison across entities | Radar chart | `references/radar-chart.md` |
| Nested proportions of hierarchical data | Treemap | `references/treemap.md` |
| End-to-end user experience with satisfaction scores | User journey | `references/user-journey.md` |
| Sequence diagram written in code-like syntax | ZenUML | `references/zenuml.md` |
| Categorizing problems by complexity domain | Cynefin framework | `references/cynefin.md` |
| Information/event flow over time (DDD-style event modeling) | Event modeling | `references/event-modeling.md` |
| Root-cause analysis (fishbone) | Ishikawa diagram | `references/ishikawa.md` |
| Formal grammar/syntax documentation (EBNF, ABNF, PEG) | Railroad diagram | `references/railroad.md` |
| Cross-functional process with clear step ownership | Swimlanes | `references/swimlanes.md` |
| Directory/file tree | TreeView | `references/tree-view.md` |
| Overlap between sets | Venn diagram | `references/venn.md` |
| Strategic value-chain mapping (build vs. buy, evolution) | Wardley map | `references/wardley.md` |

When nothing above fits cleanly, default to a flowchart with subgraphs;
it is the most flexible type.
Several of the exotic types (cynefin, event-modeling, ishikawa, railroad, swimlanes, treeView,
venn, wardley) and many `-beta` types are newer Mermaid additions:
confirm the target renderer supports them before committing to one in a canonical document.

## Rules for every diagram

The full canonical style guide, including the node color palette, edge-ID styling,
the birds-eye/technical detail-level ladder, accessibility (`accTitle`/`accDescr`),
worked don't/do examples, an agent checklist, and an anti-patterns table,
lives in `references/style-standard.md`.
Read it before producing a diagram meant for a shared doc rather than a one-off answer.

**Do:**

- Keep one diagram to one question.
  A birds-eye overview targets 6-10 nodes (12 max);
  a technical diagram stays under ~20 nodes or splits into two.
- Declare all `classDef`s before any node or edge line.
- Point an edge that crosses a subgraph boundary at the subgraph, not at a node inside it.
  The exception is a subgraph that is one stage of a straight pipeline;
  see "Subgraph edges" in `references/style-standard.md`.
- Give every subgraph an explicit id (`subgraph Proc [Process the data]`).
  A bare multi-word title is a parse error when an edge points at it.
- Write one link per line when edges need individual styling,
  and identify them with edge IDs (`Source id@--> Target`).
- Add `accTitle` and `accDescr` on diagrams meant for docs.
- Place the diagram after one sentence saying what it shows.

**Don't:**

- Don't invent a node, queue, or relationship that isn't in the source material.
  Verify names and connections against actual code/config, and say so when you can't.
- Don't use `linkStyle` index styling when the renderer supports edge IDs.
- Don't wrap a single node in a subgraph.
- Don't use `%%` comments to restate what a label already says.
- Don't let a diagram replace prose that explains non-obvious behavior.
- Don't claim a diagram renders correctly unless you actually rendered it.

## When not to draw a diagram

Say so and write prose instead when:

- The relationship is two or three items long.
  A sentence or a bullet list reads faster than a picture.
- The content is a flat list, a set of values, or a comparison table.
  That's a table, not a diagram.
- You can't verify the entities or connections against source material.
  A plausible-looking diagram is worse than no diagram, because it reads as authoritative.
- The answer is a sequence of commands or steps a reader will copy.
  Use a code block.

## Configuration and theming

Frontmatter config (`---\nconfig:\n  theme: ...\n---`), the five built-in themes, `themeVariables`,
layout engines (`dagre`, `elk`, `tidy-tree`), `look: handDrawn`,
and math rendering are covered in `references/configuration.md`.

## Embedding live-rendering Mermaid

The workflow above produces static diagram source for a doc platform to render.
When the request is instead a page or app feature that renders Mermaid diagrams live from a string at runtime (an editor,
a docs site preview, user-supplied diagram text),
see `references/embedding.md` for the JavaScript API (`initialize`/`render`/`parse`/`run`),
CDN/NPM setup, click/interactive links, and non-browser rendering options (mermaid.ink,
VS Code/Obsidian native support).

## Turning code into a diagram

- **Class diagrams:** extract classes, fields, methods, and relationships (inheritance,
  composition, aggregation, association) from the language's actual type/class declarations.
- **Sequence diagrams:** trace an actual call path (a request handler, a test,
  a script) to get real participant order and message names; don't guess a plausible-looking flow.
- **Flowcharts:** map real control flow (conditionals, loops, early returns) from the function body.
- **State diagrams:** derive states from an actual enum, status field, or state-machine definition,
  and transitions from the code paths that mutate it.
- **ER diagrams:** derive entities and relationships from the actual schema (migration files,
  ORM models), not from guessed table names.

In every case, if you can't verify a name or relationship against the source,
say so rather than inventing one.

## Common patterns

`references/common-patterns.md` has ready-to-adapt templates: API request/response flows,
auth flows (OAuth2, JWT), CI/CD pipelines, microservice and layered architectures,
common ER shapes (self-referencing, junction table, polymorphic, soft delete, audit trail),
and state-machine templates (order lifecycle, account states).

## Output format

When presenting a created or edited diagram, show:

```
Created: <filename>.mmd

<mermaid code block>

Validated with mmdc.  (or: "Not validated — no shell access to mmdc; check syntax against references/<type>.md before use.")
```

If rendered, also show the output file path.
