---
name: verify-vscode-extension
description: Use when a VS Code extension change must be checked in a real VS Code — desktop, or browser-hosted through `code serve-web` — covering its webview panels or views, its native tree views, or a defect that only reproduces inside the host (styles VS Code injects into webviews, webview link handling, tree-to-webview navigation, keyboard shortcuts, live reload, theme). Launches an isolated instance and drives it over the Chrome DevTools Protocol. Link clicks forwarded to the host show only in the browser-hosted mode.
---

# Verify a VS Code extension in a real window

Unit tests render an extension's webview UI in jsdom or to static markup.
Neither has the stylesheet VS Code injects into every webview, the nested frames a webview runs in, or the workbench's native views.
So a defect that lives in the host passes every test, and is only found by looking at a real window.

This skill launches the extension in a throwaway VS Code instance and drives it from the command line.
`scripts/vscode_cdp.mjs` does every step — launch, wait, drive, screenshot, close — with Node's built-in `fetch` and `WebSocket`, so it needs no packages and no shell utilities, and the same commands run in bash, zsh, and PowerShell.

**Needs:** Node 22 or newer and VS Code with its `code` command on `PATH` (or pass `--code <path>`).
Desktop mode needs a desktop session the window can open on; browser-hosted mode needs Chrome or Chromium and network access.

Below, `<skill>` is this skill's directory.
Every command is `node <skill>/scripts/vscode_cdp.mjs <command> ...`, shortened here to `cdp <command> ...`.
`cdp help` prints the full list.

## Pick a host

| | Desktop (`launch`) | Browser-hosted (`launch-web`) |
|---|---|---|
| What runs | an Extension Development Host window | `code serve-web` in headless Chrome |
| Loads the extension from | its source directory | a packaged `.vsix` |
| Webviews served from | `vscode-webview://` | `https://….vscode-cdn.net` |
| Link clicks forwarded to the host | invisible | visible |
| On the operator's screen | a window opens | nothing |
| Network | not needed | the first run downloads the VS Code server; webviews are served from Microsoft's `vscode-cdn.net` (not tried offline) |

Desktop is the default.
Use browser-hosted for anything about link handling, and before calling a webview change safe for code-server, Codespaces or vscode.dev users.
A green desktop run says nothing about link forwarding.
Measured with one extension's webview, its own link guard removed (VS Code 1.140, Linux, 2026-10-06): on desktop a trusted click on an in-app link reached VS Code's `window` listener and nothing opened; under `serve-web` the same click opened a "WebContentNotFound" page.
That extension's maintainers trace it to VS Code's webview host script passing every link click on to the workbench, which desktop drops for a `vscode-webview://` address (spekhq/spek issue 59); the mechanism was not measured here.

## 1. Build the extension

Build it the way its own project does, including any webview bundle.
A webview bundle is usually a separate build output; a stale one shows old UI while the source is already fixed, so rebuild it every time.
For browser-hosted mode, also package it, e.g. `npx vsce package --no-dependencies -o <file>.vsix` in the extension's directory.

## 2. Launch an isolated instance

Desktop:

```
cdp launch --extension <extension dir> --workspace <folder to open> --copy-workspace
```

Browser-hosted:

```
cdp launch-web --vsix <file.vsix> --workspace <folder to open> --copy-workspace
```

Each prints a run directory (under the system temp directory unless you pass `--run-dir`), and returns once the workbench is up.

- **Isolation.** Each instance gets its own profile (desktop: profile and extensions directory; browser-hosted: server data and Chrome profile) inside the run directory, so the operator's VS Code, settings, and extensions are untouched, and `close` shuts down exactly this instance.
- **`--copy-workspace`** opens a copy, at `<run dir>/workspace`, so anything VS Code writes into a workspace (`.vscode/`) stays out of the repository, and live-reload checks (step 6) can edit it freely.
- **Paths are made absolute** before they reach VS Code. A relative `--extensionDevelopmentPath` is silently ignored: the window opens without the extension, with no error anywhere.
- **One instance per port.** Both refuse a DevTools port that anything listens on; pass `--port` to run a second one, and `--web-port` for a second `serve-web`. A port that accepts connections but never answers is refused within two seconds, naming how to find what holds it, since VS Code could not bind it (step 9 says how that happens).

Desktop only:

- **Installed extensions are disabled.** The development extension still loads; the "All installed extensions are temporarily disabled" notification is expected.
- **A window opens on the operator's screen.** Say so before launching.

Browser-hosted only:

- **The server license.** `launch-web` passes `--accept-server-license-terms`, accepting the VS Code Server license on the operator's behalf. Say so before the first run.
- **The first run downloads the VS Code server** matching the installed `code` into the user cache directory (`--cache-dir` to change it); later runs reuse it. It took 15–30 seconds on Linux. A request is what starts that download, and the server answered 202 while downloading and 302 once it ran, so `launch-web` waits for the 302 before it installs anything.
- **The folder is trusted for you.** It opens in Restricted Mode, which disables an extension that declares no untrusted-workspace support, so the extension's commands are missing and the palette silently runs whatever command matches instead. Writing the trust setting into the server's settings did not change that; `launch-web` clicks "Trust" in the trust editor.
- **Every request carries a connection token**, written to the run directory, and the server listens on localhost.
- **After rebuilding**, package again and run `cdp install --vsix <file.vsix>`: it reinstalls over the old copy and reloads the page. Open the extension's view again afterwards.

## 3. Open what you are checking

```
cdp palette "<command title as it appears in the palette>"
```

Use the extension's own command to open its webview, and `View: Show <container title>` to open its activity-bar container.
`cdp targets` then lists each webview as an `iframe` target whose URL carries `extensionId=<publisher.name>`, on both hosts.
The palette opens with Ctrl+Shift+P (Cmd+Shift+P on macOS); in headless Chrome Ctrl+Shift+P opened it too.

## 4. Drive and read a webview

A webview target's own document is VS Code's host frame; the extension's page is the iframe inside it.
These commands reach that inner document for you:

```
cdp click-link "<href>"
cdp click-app "<css selector>"
cdp fill "<css selector>" "<value>"
cdp rows "<css selector>"
```

- `click-link` matches the `href` *attribute*, which suits client-side routes (`/settings`) that have no visible text to match on. It sends a real mouse click (a trusted event) at the link's position in the workbench, so VS Code's own listeners see what a user's click produces — which is what link-handling checks depend on.
- `click-app` does the same for any other element, such as a button.
- `fill` sets the value through the native setter and dispatches `input`, which is what React and similar frameworks listen for; assigning `.value` alone changes nothing they can see.
- `rows` prints each match's text on its own line. When lists nest, pick a selector that matches one row per item, not the wrapper around a nested list as well — otherwise a subtree prints twice.
- With several webviews open, add `--extension-id <publisher.name>`.

For anything else, put one JavaScript expression in a file and evaluate it; inside a webview the extension's document is bound as `d`:

```
cdp webview --file check.js
```

An expression that yields `null` or `undefined` prints `null`: the webview was reached, and what you asked for is not there.
With several webviews open, the first answer that is not `null` or `undefined` wins.
Use a file rather than an inline string: the quoting an inline expression needs differs between bash, PowerShell, and cmd.exe.

### Keyboard

```
cdp click-app "<something focusable, or any element>"
cdp key Ctrl+K
cdp type "some text"
cdp key ArrowDown
cdp key Enter
```

`key` presses one key or combo (`Alt`, `Ctrl`, `Meta`, `Shift`; letters, digits, `Enter`, `Escape`, `Tab`, arrows and a few more — `cdp help`), and `type` inserts text.
Both go wherever focus is, as a user's keys would, so click into the webview first.
Measured with one extension's webview on both hosts (2026-10-06): after a click into it, Ctrl+K reached the extension's own shortcut handler, typed text landed in the input it opened, and ArrowDown + Enter picked a result.
On desktop, with focus in a native tree instead, Ctrl+K never reached the webview: VS Code took it as the start of a chord.
Even with the webview focused, VS Code also started that chord, and the next real key was offered to both — `key a` landed in the input while the status bar reported "(Ctrl+K, A) is not a command".
A key that completes a bound chord would presumably also run that command (not verified).
`type` inserts text without key events, so it never meets a keybinding; use `key` per character when keybindings are what you are checking.
On macOS pass `Meta` where a shortcut means Cmd (not verified).

### Check that link clicks stay in the webview (browser-hosted)

```
cdp targets
cdp click-link "<an in-app href>"
cdp targets
```

The second listing must hold the same `page` targets as the first; a forwarded click shows up as an extra `page`.

## 5. Read and click native views

```
cdp tree-rows <view container id>
cdp click-row <view container id> "<label>"
cdp expand-row <view container id> "<label>"
cdp click "<css selector>"
cdp workbench --file check.js
```

`tree-rows` takes the container id from the extension's `contributes.viewsContainers`, and prints each row's displayed label, followed by its description when it has one.
`click-row` mouse-clicks the row whose displayed label equals `<label>`; `expand-row` clicks that row's expand arrow.
Both match the label a row shows, not its `aria-label`: VS Code fills that from the item's tooltip when it has one, so it can be a path, a raw heading, or a title plus a date (observed 2026-10-06).
Labels can repeat across folders, and the first rendered match wins, so expand only the folder you need.
Folders start collapsed, so a row inside one is not there to click until it is expanded; clicking a row that has a command runs the command and may not expand it.
`click` mouse-clicks any workbench element.

When a tree item scrolls a webview to a position, check it against content long enough to scroll: on a page that fits the window, opening the page and jumping to the anchor look the same.
Read the webview's `scrollY` and the target's `getBoundingClientRect().top` before and after.

## 6. Check live reload

With `--copy-workspace`, edit `<run dir>/workspace` from the shell — add a file, rename a directory — wait a few seconds, then read the webview and the tree again.
Include a directory rename: one extension's live reload once caught file edits and missed directory moves.

## 7. Check both themes

```
cdp palette "Preferences: Toggle between Light/Dark Themes"
```

Then read the webview's `document.body.className` (`vscode-light` / `vscode-dark`) and take a screenshot.
Desktop started dark; headless Chrome started light, probably following the browser's own colour scheme (observed, cause not established).
Toggle rather than pick from "Preferences: Color Theme": typing a theme name there and pressing Enter selected "Browse Additional Color Themes…" and left the marketplace picker open, while the webview showed only a preview of the theme, never saved (VS Code 1.140, whose built-in themes are "Dark 2026" and "Light 2026").

## 8. Look at the window

```
cdp shot window.png
```

Always take a screenshot and look at it.
Text checks cannot see the defects this skill exists for: a background VS Code injected, a light panel holding a dark chip, a label cut short.

## 9. Close

```
cdp close
```

This sends the DevTools `Browser.close` command, which shuts down the whole isolated desktop instance or the headless Chrome, waits for its connection to drop, then waits until nothing listens on its port.
After `launch-web` it also stops the `serve-web` server and everything it started, and waits until the web port is free.
The run directory is left in place for its screenshots; delete it when done.

If it fails with "the instance closed, but port … accepts connections and never answers", the instance is gone and a process outside it still holds the DevTools socket; a launch on that port would fail.
Find the holder (Linux: `ss -ltnp`; macOS: `lsof -iTCP:<port> -sTCP:LISTEN`; Windows: `netstat -ano`) and stop it.
On Ubuntu 20.04 (GNOME on X11, VS Code 1.134, reported by another operator) that holder was a `dconf watch /system/proxy/` started alongside the window and reparented to `systemd --user`, and stopping that one process freed the port.
It did not happen on Arch Linux with GNOME Shell 51 on Wayland, VS Code 1.141 (2026-10-08); what decides whether the watcher starts is not established.
Before every request carried a timeout, `close` waited on such a port forever.

Close the instance this way; do not "simplify" it to a kill.
Measured on Linux, VS Code 1.140.0, 2026-10-06:

- The `code` launcher exits once the window is up, and the window's main process is reparented (parent PID 1), so the PID a script gets from starting `code` is not the window's.
- A pattern kill on the profile path also matches the window's GPU and utility processes, and the window survived the first SIGTERM in three of four runs. Why was not established. A pattern kill can also match the shell running it, whose own command line holds the pattern.
- One second after `Browser.close`, no process of the instance was left.
- A launch sharing a running instance's profile starts no instance of its own: its window opens inside the running one, and its `--remote-debugging-port` is ignored, so nothing answers on that port. When the running instance does have a debug port, `Browser.close` there closes all of its windows. Both were measured with two launches sharing a throwaway profile, standing in for the operator's default one. This is why every launch gets its own `--user-data-dir`.
- Killing `serve-web`'s launcher processes left the server it had started running, reparented to PID 1, still holding its extension hosts. `launch-web` therefore starts the launcher detached — on POSIX that makes it a process-group leader — and `close` signals the whole group, which stopped every process and freed the port. On Windows `close` uses `taskkill /T` instead (not yet run).

Signalling the desktop window's main process directly would mean finding it by the port it serves; the lookup tried for that (`ss` and `/proc`) exists only on Linux, and none was tried on Windows or macOS.

## Platform notes

Measured on Linux (X11), VS Code 1.140.0, Node 24.14.0, Google Chrome, 2026-10-06: every command above, end to end, on both hosts.
Re-run on Arch Linux, GNOME Shell 51 on Wayland (VS Code on native Wayland), VS Code 1.141.0, Node 26.11.1, Google Chrome, 2026-10-08: `launch`, `launch-web`, `palette`, `click-link`, `click-app`, `fill`, `rows`, `key`, `type`, `webview`, `tree-rows`, `click-row`, `targets`, `shot` and `close`, against one extension.
Reported by another operator on Ubuntu 20.04, GNOME on X11, VS Code 1.134, Node 22, running the same steps through the spek repository's copy of this driver rather than this script: the desktop host behaved as written apart from the leaked listener in step 9.
**Not yet run on Windows or macOS.** What differs there is handled in the script, but unverified:

- **Windows** starts `code.cmd`, which Node can only run through a shell, so each argument is quoted for cmd.exe. The server's own CLI is `code-server.cmd`, run the same way, and `close` stops the server with `taskkill /T /F`. Chrome is looked for under `%ProgramFiles%`, `%ProgramFiles(x86)%` and `%LOCALAPPDATA%`. Whether `serve-web` accepts a Windows path in the URL's `folder=` as given is untested.
- **macOS** opens the palette with Cmd+Shift+P instead of Ctrl+Shift+P. `code` is on `PATH` only after VS Code's "Shell Command: Install 'code' command in PATH"; otherwise pass `--code`. Chrome is looked for in `/Applications`.
- **Chromium** is in the Linux candidate list but was not run; `--chrome <exe>` picks a browser explicitly on any platform.

## Why the script is Node, not Python

Python is the default for scripts with real logic, and this one would be Python if the standard library could do the job.
It cannot: everything here goes over the DevTools Protocol, which is a WebSocket connection, and Python's standard library has no WebSocket client.
The options were all worse than switching language:

- **A third-party package** (`websockets`, `websocket-client`) means an install step before the skill can run, and a dependency to keep working on every platform.
- **Hand-writing the protocol** on `asyncio` streams means implementing the RFC 6455 handshake, frame masking, and fragmentation — a hundred-odd lines of networking code that exist only to send a few JSON messages.

Node 22 ships both pieces built in: `fetch` for the HTTP endpoints that list targets, and a global `WebSocket` for the protocol itself.
And anyone building a VS Code extension already has Node, since extensions are built with it — so choosing Node adds no requirement that the task did not already impose.

## What this does not cover

- **Remote and container workspaces** (Remote-SSH, Dev Containers, WSL), which run the extension host elsewhere.
- **vscode.dev and Codespaces themselves.** `serve-web` serves its webviews the way they do (an `https://` origin), which is what the link-forwarding check relies on; anything specific to those services is not exercised.
