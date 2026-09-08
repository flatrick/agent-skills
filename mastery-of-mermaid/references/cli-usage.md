# CLI usage (mmdc)

The Mermaid CLI (`@mermaid-js/mermaid-cli`, binary name `mmdc`) is the harness-agnostic way to
validate and render diagrams: a plain command-line tool, not tied to any particular agent or
editor. Requires Node.js `^18.19` or `>=20.0`.

## Installing

| Method | Command | When to use |
|---|---|---|
| Global | `npm install -g @mermaid-js/mermaid-cli` | You'll validate/render diagrams repeatedly in this environment. |
| Local (project dependency) | `npm install @mermaid-js/mermaid-cli` then `./node_modules/.bin/mmdc -h` | Pin the version alongside the project instead of relying on global state. |
| No install | `npx -p @mermaid-js/mermaid-cli mmdc -h` | One-off use, or no permission to install globally. |
| Docker | `docker pull ghcr.io/mermaid-js/mermaid-cli/mermaid-cli` | No Node.js available at all. |

If none of these are available (no shell access, or install blocked), fall back to eyeballing
syntax against the relevant `references/<type>.md` file and say plainly that the diagram is
unverified. See `references/configuration.md` for a JavaScript-only validation alternative
(`mermaid.parse()`) when a JS runtime is available but the CLI is not.

## Basic commands

```bash
mmdc -i input.mmd -o output.svg   # SVG (default, preferred for docs)
mmdc -i input.mmd -o output.png
mmdc -i input.mmd -o output.pdf
```

Output format is inferred from the output file's extension.

## Useful flags

| Flag | Effect |
|---|---|
| `-i, --input <file>` | Input file. Use `-` to read from stdin. |
| `-o, --output <file>` | Output file path. |
| `-t, --theme <name>` | `default`, `dark`, `forest`, `neutral`, `base`. |
| `-b, --background <color>` | `transparent`, `white`, or a `#hex` value. |
| `-w, -H` | Custom width/height in pixels. |
| `--cssFile <file>` | Extra CSS applied to the rendered SVG. |
| `--configFile <file>` | A Mermaid config JSON file (same shape as frontmatter `config:`). |
| `--iconPacks <pkg>` | Register an iconify.design icon pack for architecture/flowchart icons. |
| `-h, --help` | Full flag list, since versions add flags over time. |

```bash
mmdc -i diagram.mmd -o output.png -t dark -b transparent --cssFile custom.css --configFile mermaid-config.json
```

## Validating without producing a file

```bash
mmdc -i diagram.mmd -o /dev/null && echo "valid" || echo "invalid syntax"
```

On Windows, use `NUL` instead of `/dev/null`. This is the fastest way to check syntax when you
don't need the rendered image.

## Stdin and batch processing

```bash
cat diagram.mmd | mmdc -i - -o output.svg
```

```bash
for file in *.mmd; do
  mmdc -i "$file" -o "${file%.mmd}.svg"
done
```

## Rendering diagrams embedded in a markdown file

`mmdc` can process a markdown file directly, rendering every ` ```mermaid ` block to an image
and rewriting the references, useful for a docs build step rather than one-off diagram files:

```bash
mmdc -i README.template.md -o README.md
```

## Docker and Podman

```bash
docker run --rm -v "$(pwd):/data" ghcr.io/mermaid-js/mermaid-cli/mermaid-cli -i /data/input.mmd -o /data/output.svg
```

Add `-u $(id -u):$(id -g)` on Docker if the container writes files owned by root on the host.

```bash
podman run --userns keep-id --user "${UID}" --rm -v /path/to/diagrams:/data:z ghcr.io/mermaid-js/mermaid-cli/mermaid-cli -i diagram.mmd
```

## Troubleshooting

- **Large diagrams run out of memory:** `NODE_OPTIONS="--max-old-space-size=4096" mmdc -i large.mmd -o out.svg`. If a diagram routinely needs this, it's also a signal to split it, see the node-count guidance in `references/style-standard.md`.
- **Docker output owned by root:** add `-u $(id -u):$(id -g)`.
- **A previously-working diagram suddenly fails to parse:** check whether the Mermaid CLI version changed; syntax that's valid in v11 can differ from v9/v10 (see `maxTextSize`/`maxEdges` limits in `references/configuration.md` for another common silent-failure cause on very large diagrams).

## Node.js API (programmatic use)

For scripting rendering directly in a Node.js process instead of shelling out:

```javascript
import { run } from '@mermaid-js/mermaid-cli'

await run('input.mmd', 'output.svg', {
  theme: 'dark',
  backgroundColor: 'transparent',
})
```

## CI example

```yaml
- name: Generate diagrams
  run: |
    npm install -g @mermaid-js/mermaid-cli
    mmdc -i docs/diagram.mmd -o docs/diagram.svg
```

The `scripts/verify-diagrams.ps1` script in this skill automates the same idea across every
diagram documented here, extract every example, render each with `mmdc`, report failures.
