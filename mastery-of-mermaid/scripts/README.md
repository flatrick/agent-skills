# Verification scripts

Prove the diagrams documented in this skill actually render, instead of trusting that the
syntax looks right. Every ` ```mermaid ` fenced code block under `../references/` and
`../SKILL.md` gets extracted, rendered with the real Mermaid CLI, and reported pass/fail.

Run this after editing any reference file, and before adding a new diagram type or example.

## Requirements

- [Node.js](https://nodejs.org) and the Mermaid CLI: `npm install -g @mermaid-js/mermaid-cli`
  (provides the `mmdc` command used to render each block).
- PowerShell 7+ (`pwsh`) for `verify-diagrams.ps1`. Windows PowerShell 5.1 has not been tested.

A Python equivalent for non-Windows shells without `pwsh` is planned but not yet written; for
now, PowerShell 7 runs fine on macOS and Linux too (`pwsh verify-diagrams.ps1`).

## Usage

```
pwsh ./verify-diagrams.ps1
```

Defaults to scanning the skill folder this script lives in (one level up) and writing
temporary render output to the system temp folder, which it deletes automatically when
every block passes.

Options:

| Flag | Effect |
|---|---|
| `-SkillDir <path>` | Scan a different folder of markdown files instead of this skill. |
| `-OutDir <path>` | Write extracted `.mmd`/rendered `.svg`/error logs somewhere specific. |
| `-KeepArtifacts` | Keep the output folder even when everything passes. |
| `-Render` | Keep rendered images and embed fallback links in the docs (see below), instead of validating and discarding. |

Output is always kept, regardless of `-KeepArtifacts`, when at least one block fails, so the
failing `.mmd` source and the `.err.log` with the actual Mermaid CLI error are there to inspect.

## Rendering fallback images (`-Render`)

```
pwsh ./verify-diagrams.ps1 -Render
```

Some markdown renderers either don't support Mermaid at all, or only support an older version
that can't parse this skill's Mermaid 11.x syntax (edge IDs, `@{ curve: ... }`, `wardley-beta`,
`swimlane-beta`, C4, and similar). `-Render` renders every ` ```mermaid ` block to a real,
kept SVG under `references/rendered/`, and inserts a fallback image link right after each
block so those renderers still show a correct diagram, while the raw mermaid source stays
in place for renderers that can render it live.

Each block gets a stable id marker (`<!-- mermaid-render: id="..." -->`) directly above the
fence, bootstrapped automatically the first time a block is rendered. The id is what ties a
block to its image filename and its embedded link, so it's assigned once and never recomputed
from position — reordering or adding blocks elsewhere in the file won't reassign or desync an
already-rendered image.

This mode edits the source markdown files in place and is meant to be run locally after adding
or editing a diagram, not as part of CI (use the default, non-`-Render` mode for that). It's
safe to re-run: existing markers and image links are recognized and updated, not duplicated. A
block that fails to render leaves its previous marker and image (if any) untouched and is
reported as a failure rather than corrupting the doc.

## What counts as a failure

A block fails when `mmdc` exits non-zero rendering it, a real Mermaid syntax or semantic error,
not a style-guide opinion. The script's own exit code is `0` when every block renders, `1` when
at least one fails, and `2` when `mmdc` isn't installed at all.

## What this doesn't check

- Visual correctness (whether the rendered diagram looks the way the prose says it should).
- The plain, non-` ```mermaid ` "Source" code blocks in `style-standard.md` (each one is
  paired with an identical ` ```mermaid ` "Rendered" block right after it, which this script
  does check).
- Prose accuracy of anything not expressed as a fenced Mermaid block.
