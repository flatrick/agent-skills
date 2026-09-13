# Verification script

Prove the diagrams documented in this skill actually render,
instead of trusting that the syntax looks right.
Every ` ```mermaid ` fenced code block under `../references/` and `../SKILL.md` gets extracted,
rendered with the real Mermaid CLI, and reported pass/fail.

Run this after editing any reference file, and before adding a new diagram type or example.

## Requirements

- [Node.js](https://nodejs.org) and the Mermaid CLI:
  `npm install -g @mermaid-js/mermaid-cli` (provides the `mmdc` command used to render each block).
- Python 3.9 or newer.

## Usage

```
python3 scripts/render-diagrams.py                              # render new blocks, wire up markup
python3 scripts/render-diagrams.py --check                      # validate only, edit nothing
python3 scripts/render-diagrams.py --file references/erd.md     # limit to one file
python3 scripts/render-diagrams.py --force                      # re-render images that already exist
```

| Flag | Effect |
|---|---|
| `--check` | Validate only. Renders every block to a throwaway path and edits nothing. Use this in CI or a pre-commit hook. |
| `--file <path>` | Limit the run to one markdown file. Repeatable. |
| `--force` | Re-render images that already exist, not just missing ones. Use after editing an existing diagram. |
| `--skill-dir <path>` | Scan a different folder of markdown files instead of this skill. |
| `--artifact-dir <path>` | Where to keep the `.mmd` and full log of any block that fails to render. |

## What it does

For each ` ```mermaid ` block it assigns a stable id (`<file stem>--block<n>`) if the block has none,
renders the SVG to `references/rendered/`,
inserts the `<!-- mermaid-render: id="..." -->` marker above the fence,
and inserts an `<img>` fallback link directly below it.

The fallback image matters because some markdown renderers either don't support Mermaid at all,
or only support an older version that can't parse this skill's Mermaid 11.x syntax (edge IDs,
`@{ curve: ... }`, `wardley-beta`, `swimlane-beta`, C4, and similar).
The raw mermaid source stays in place for renderers that can render it live.

The id is what ties a block to its image filename and its embedded link,
so it's assigned once and never recomputed from position.
Reordering or adding blocks elsewhere in the file won't reassign or desync an already-rendered image.

A width is computed from the rendered SVG's own `viewBox` when an image link is first inserted.
An existing width is never rewritten, because several are hand-tuned.

## It is safe to re-run

A second run over an unchanged file changes nothing.
Images that already exist are not re-rendered unless you pass `--force`,
because `mmdc` embeds nondeterministic ids and re-rendering an unchanged block would churn the file for no reason.

A block that fails to render is reported and left exactly as it was, rather than corrupting the doc.
Its `.mmd` source and the full `mmdc` log are kept under the artifact directory so you can inspect the exact input and re-run it by hand.

## What counts as a failure

A block fails when `mmdc` exits non-zero rendering it, a real Mermaid syntax or semantic error,
not a style-guide opinion.
The reported error is Mermaid's own parse message with its line number and caret;
the Puppeteer stack trace that `mmdc` prints after it goes to the log file, not the terminal.

Exit codes: `0` when every block renders, `1` when at least one fails, `2` when `mmdc` isn't installed.

## What this doesn't check

- Visual correctness (whether the rendered diagram looks the way the prose says it should).
- The plain,
  non-` ```mermaid ` "Source" code blocks in `style-standard.md` (each one is paired with an identical ` ```mermaid ` "Rendered" block right after it,
  which this script does check).
- Prose accuracy of anything not expressed as a fenced Mermaid block.
