#!/usr/bin/env python3
"""Render every ```mermaid block in the skill and keep its id marker and fallback image in sync.

It understands this skill's committed markup: a stable id marker above each fence and an <img>
fallback below it, so markdown renderers without current Mermaid support still show a correct
diagram.

    python3 scripts/render-diagrams.py            # render new/changed blocks, wire up markup
    python3 scripts/render-diagrams.py --check    # validate only, touch nothing, exit 1 on failure
    python3 scripts/render-diagrams.py --file references/flowchart.md

Widths on existing <img> lines are left alone; they are hand-tuned in places. A width is only
computed (from the rendered viewBox, clamped) when an <img> line is first inserted.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# The marker above and the <img> below are both optional, so this matches a brand-new block too.
# Some committed blocks separate the fence from their <img> by a blank line; that gap is captured
# so it round-trips instead of the image being duplicated.
BLOCK = re.compile(
    r'(?:^<!-- mermaid-render: id="(?P<id>[^"]+)" -->\n)?'
    r'^```mermaid\n(?P<code>.*?)\n```\n'
    r'(?P<gap>\n*)'
    r'(?P<img>^<img src="[^"]+"[^>]*>\n)?',
    re.S | re.M,
)
# Offsets are routinely negative (Mermaid pads the canvas), so every number needs an optional sign.
NUM = r"-?[\d.]+"
VIEWBOX = re.compile(rf'viewBox="{NUM} {NUM} ({NUM}) ({NUM})"')
MIN_WIDTH, MAX_WIDTH = 150, 1400


def rendered_width(svg_path: str) -> int:
    """Pick a display width from the SVG's own viewBox, clamped to something readable."""
    try:
        with open(svg_path, encoding="utf-8") as fh:
            m = VIEWBOX.search(fh.read(4096))
    except OSError:
        return 600
    if not m:
        return 600
    return max(MIN_WIDTH, min(MAX_WIDTH, int(round(float(m.group(1))))))


MERMAID_ERROR = re.compile(
    r"(Parse error|Syntax error|Error:|Expecting |UnknownDiagramError|No diagram type detected)"
)


def summarize_error(raw: str) -> str:
    """Pull Mermaid's own complaint out of mmdc's output.

    mmdc prints the useful parse error first and then a long Puppeteer stack trace. The stack is
    noise for someone fixing a diagram, and blindly keeping the tail throws away the line number
    and caret that actually locate the problem.
    """
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    start = next((i for i, ln in enumerate(lines) if MERMAID_ERROR.search(ln)), None)
    if start is None:
        return "\n".join(lines[:10]).strip()
    kept = []
    for ln in lines[start:]:
        # The stack trace begins at the first "at ..." frame; everything before it is the message.
        if ln.lstrip().startswith("at ") or "node_modules" in ln:
            break
        kept.append(ln)
    return "\n".join(kept[:12]).strip()


def render(
    mmdc: str, code: str, svg_path: str, artifact_dir: str, block_id: str
) -> tuple[bool, str]:
    """Run mmdc on one block. Returns (ok, summarized error).

    On failure the block's .mmd source and the full mmdc log are kept under artifact_dir, so the
    exact input that failed can be inspected and re-run by hand.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as fh:
        fh.write(code)
        src = fh.name
    try:
        proc = subprocess.run(
            [mmdc, "-i", src, "-o", svg_path], capture_output=True, text=True
        )
        if proc.returncode == 0:
            return True, ""
        raw = (proc.stderr or "") + (proc.stdout or "")
        os.makedirs(artifact_dir, exist_ok=True)
        with open(os.path.join(artifact_dir, f"{block_id}.mmd"), "w", encoding="utf-8") as fh:
            fh.write(code)
        with open(os.path.join(artifact_dir, f"{block_id}.err.log"), "w", encoding="utf-8") as fh:
            fh.write(raw)
        return False, summarize_error(raw)
    finally:
        os.unlink(src)


def process(
    mmdc: str, md_path: str, skill_dir: str, check_only: bool, force: bool, artifact_dir: str
) -> tuple[int, list[tuple[str, str, str]]]:
    """Render every block in one markdown file. Returns (total, failures)."""
    with open(md_path, encoding="utf-8") as fh:
        text = fh.read()

    stem = os.path.splitext(os.path.basename(md_path))[0]
    rel_to_refs = os.path.relpath(
        os.path.join(skill_dir, "references", "rendered"), os.path.dirname(md_path)
    ).replace(os.sep, "/")

    used = {m.group("id") for m in BLOCK.finditer(text) if m.group("id")}
    counter = [0]

    def next_id() -> str:
        while True:
            counter[0] += 1
            candidate = f"{stem}--block{counter[0]}"
            if candidate not in used:
                used.add(candidate)
                return candidate

    total: int = 0
    failures: list[tuple[str, str, str]] = []
    out: list[str] = []
    cursor: int = 0

    for m in BLOCK.finditer(text):
        total += 1
        out.append(text[cursor:m.start()])
        cursor = m.end()

        code = m.group("code")
        block_id = m.group("id") or next_id()
        svg_dir = os.path.join(skill_dir, "references", "rendered")
        os.makedirs(svg_dir, exist_ok=True)
        svg_path = os.path.join(svg_dir, f"{block_id}.svg")

        # mmdc embeds nondeterministic ids, so re-rendering an unchanged block churns the SVG for
        # no reason. Committed images are left alone unless they are missing or --force is given;
        # validation still renders every block, just to a throwaway path.
        keep_existing = os.path.exists(svg_path) and not force
        target = os.path.join(tempfile.gettempdir(), f"{block_id}.svg") \
            if (check_only or keep_existing) else svg_path

        ok, err = render(mmdc, code, target, artifact_dir, block_id)
        if not ok:
            failures.append((md_path, block_id, err))
            # Leave a failing block exactly as it was rather than corrupting the doc.
            out.append(m.group(0))
            continue

        if check_only:
            out.append(m.group(0))
            continue

        img = m.group("img")
        if img is None:
            width = rendered_width(target)
            img = f'<img src="{rel_to_refs}/{block_id}.svg" alt="{block_id}" width={width}px/>\n'
        # The image belongs directly under the fence, with any blank line after it rather than
        # before. Emitting it this way normalizes blocks that were written the other way round.
        out.append(
            f'<!-- mermaid-render: id="{block_id}" -->\n'
            f"```mermaid\n{code}\n```\n"
            f'{img}{m.group("gap")}'
        )

    out.append(text[cursor:])
    new_text = "".join(out)
    if not check_only and new_text != text:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        print(f"updated {os.path.relpath(md_path, skill_dir)}")

    return total, failures


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", default=os.path.dirname(here))
    parser.add_argument("--file", action="append", default=[],
                        help="Limit to these markdown files (repeatable).")
    parser.add_argument("--check", action="store_true",
                        help="Validate only: render to temp, never edit the docs.")
    parser.add_argument("--force", action="store_true",
                        help="Re-render images that already exist, not just missing ones.")
    parser.add_argument("--artifact-dir", default=None,
                        help="Where to keep the .mmd and full log of any block that fails to "
                             "render (default: a mermaid-verify-* folder under the temp dir).")
    args = parser.parse_args()

    # Pass the resolved path, not the bare name: Windows process creation ignores PATHEXT,
    # so a bare "mmdc" cannot launch npm's mmdc.cmd shim.
    mmdc = shutil.which("mmdc")
    if mmdc is None:
        print("mmdc (Mermaid CLI) not found on PATH. "
              "Install it with: npm install -g @mermaid-js/mermaid-cli", file=sys.stderr)
        sys.exit(2)

    skill_dir = os.path.abspath(args.skill_dir)
    artifact_dir = args.artifact_dir or os.path.join(
        tempfile.gettempdir(), "mermaid-verify-artifacts"
    )
    if args.file:
        targets = [os.path.abspath(f) for f in args.file]
    else:
        targets = sorted(
            os.path.join(root, name)
            for root, _, names in os.walk(skill_dir)
            for name in names
            if name.endswith(".md")
        )

    total: int = 0
    failures: list[tuple[str, str, str]] = []
    for md in targets:
        t, f = process(mmdc, md, skill_dir, args.check, args.force, artifact_dir)
        total += t
        failures.extend(f)

    print(f"TOTAL BLOCKS: {total}")
    print(f"FAILED: {len(failures)}")
    for path, block_id, err in failures:
        print(f"---- {os.path.relpath(path, skill_dir)} [{block_id}]")
        print(err)
    if failures:
        print(f"\nFailing source and full logs kept at: {artifact_dir}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
