# Embedding live-rendering Mermaid

Everything else in this skill produces static diagram source,
a `.mmd` file or a ` ```mermaid ` fence meant for a doc platform (GitHub, GitLab, Notion, Obsidian, Confluence, VS Code) to render. This file covers wiring the `mermaid` JavaScript library into a page or app so it renders diagrams live,
at runtime, from a string.

**Use for:** an interactive page or app feature (a diagram editor, a docs site with a live preview,
user-supplied diagram text rendered on the fly).
**Avoid for:** creating a diagram to embed as a static `.mmd` file;
use the core workflow in `SKILL.md` instead,
most doc platforms already render Mermaid fences natively.

## Browser via CDN

```html
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'
  mermaid.initialize({ startOnLoad: true })
</script>
<pre class="mermaid">
  flowchart TD
    A[Client] --> B[Server]
</pre>
```

Pin a specific major version (`mermaid@11`,
not `@latest`) in anything meant to keep rendering the same way over time.

## NPM

```bash
npm install mermaid
```

```javascript
import mermaid from 'mermaid'

mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' })

const { svg } = await mermaid.render('diagram-id', diagramSource)
container.innerHTML = svg
```

This `initialize` once, then `render(id, source)` per diagram,
pattern is the same regardless of which UI framework wraps it:
call `render` when the component mounts and again whenever `diagramSource` changes,
then set the returned `svg` as the container's inner HTML.

## Core API surface

- `mermaid.initialize(config)` — one-time global config (theme, security level, fonts);
  see `references/configuration.md` for available options.
- `mermaid.render(id, source)` — renders one diagram, returns `{ svg, bindFunctions }`.
  `id` must be unique per call.
- `mermaid.parse(source)` — validates syntax without rendering; throws on invalid syntax.
  See the validation section of `references/configuration.md`.
- `mermaid.run(config)` — finds and renders every element matching `config.querySelector` (default `.mermaid`) on the page;
  the CDN quick-start above uses this implicitly via `startOnLoad: true`.

## Interactive diagrams

Click handlers and links are declared in the diagram source itself, not wired up separately:

```
flowchart TD
    A[GitHub] --> B[Docs]
    click A "https://github.com" "Open GitHub"
    click B callback "Run a JS callback instead of a link"
```

`click <nodeId> callback` calls a function of that name in global scope;
`click <nodeId> "<url>"` opens a link.
Requires `securityLevel: 'loose'` (the default `strict` HTML-encodes labels and suppresses interactivity),
so only use it on diagrams you trust, not on unsanitized user input.

## Re-rendering on theme change

```javascript
function updateTheme(isDark) {
  mermaid.initialize({ theme: isDark ? 'dark' : 'default', startOnLoad: false })
  document.querySelectorAll('.mermaid').forEach(async (el) => {
    const { svg } = await mermaid.render('diagram-' + Math.random(), el.textContent)
    el.innerHTML = svg
  })
}
```

Mermaid has no built-in reactive theme switching,
changing `theme` after the fact requires re-rendering every diagram on the page from its original source text.

## Non-browser rendering

- **VS Code:** the "Markdown Preview Mermaid Support" extension renders fences natively;
  no embedding code needed.
- **Obsidian, Notion, Confluence, GitHub, GitLab:** render ` ```mermaid ` fences natively.
- **Jupyter or any non-JS context:** the [mermaid.ink](https://mermaid.ink) service renders a diagram string server-side and returns an image,
  useful when the environment can make an HTTP request but can't run the JS library.
- **PowerPoint or Word:** no native renderer,
  paste the diagram into [mermaid.live](https://mermaid.live), export as PNG/SVG,
  and insert the image.
