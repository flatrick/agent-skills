#!/usr/bin/env node
// Launches an isolated VS Code — a desktop Extension Development Host, or a browser-hosted one
// (`code serve-web` in headless Chrome) — and drives it over the Chrome DevTools Protocol.
// Node 22+ (built-in fetch and WebSocket); no dependencies, no shell utilities.
//
// Run `node vscode_cdp.mjs help` for the command list.
import { spawn, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const DEFAULT_PORT = 9333;
export const DEFAULT_WEB_PORT = 8123;

const USAGE = `usage: node vscode_cdp.mjs <command> [options]

  launch --extension <dir> --workspace <dir> [--copy-workspace] [--run-dir <dir>] [--code <exe>]
                                   start an isolated desktop window; prints the run directory
  launch-web --vsix <file> --workspace <dir> [--copy-workspace] [--run-dir <dir>] [--code <exe>]
             [--chrome <exe>] [--web-port <n>] [--cache-dir <dir>]
                                   start a browser-hosted VS Code (code serve-web) in headless Chrome,
                                   install the .vsix, and trust the folder; prints the run directory
  install --vsix <file>            browser-hosted only: reinstall the extension and reload the page
  close                            close the instance (and, browser-hosted, stop its server)
  targets                          list CDP targets
  palette <command text>           run a command through the command palette
  click-link <href>                mouse-click the first <a> in the webview whose href attribute equals <href>
  click-app <css selector>         mouse-click the first webview element matching the selector
  click-row <view container id> <label>
                                   mouse-click the native tree row whose displayed label is <label>
  expand-row <view container id> <label>
                                   mouse-click that row's expand/collapse arrow
  click <css selector>             mouse-click the first workbench element matching the selector
  key <combo>                      press a key where focus is: Ctrl+K, Meta+K, Enter, ArrowDown, a, …
  type <text>                      insert text where focus is
  fill <css selector> <value>      set an input's value so frameworks (React, Vue) see the change
  rows <css selector>              print the innerText of every match in the webview, one per line
  tree-rows <view container id>    print the rows of a native tree view in a sidebar container
  webview --file <js file>         evaluate an expression in the webview; \`d\` is its document
  workbench --file <js file>       evaluate an expression in the workbench page
  shot <file.png>                  screenshot the workbench

common options:
  --port <n>              DevTools port (default ${DEFAULT_PORT})
  --extension-id <id>     with several webviews open, use the one from this extension (publisher.name)
  --timeout <seconds>     how long launch waits for the window (default 90; launch-web 180)`;

/** Splits argv into positionals and `--name value` / `--flag` options. */
export function parseArgs(argv) {
  const flags = new Set(["copy-workspace"]);
  const positionals = [];
  const options = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const name = arg.slice(2);
      if (flags.has(name)) options[name] = true;
      else {
        if (i + 1 >= argv.length) throw new Error(`--${name} needs a value`);
        options[name] = argv[++i];
      }
    } else positionals.push(arg);
  }
  return { positionals, options };
}

/** Command-palette modifiers as CDP bits: Ctrl=2, Meta=4, Shift=8. */
export function paletteModifiers(platform = process.platform) {
  return (platform === "darwin" ? 4 : 2) | 8;
}

/**
 * How to start the `code` launcher. On Windows it is `code.cmd`, which Node only runs through a shell,
 * so every argument is quoted for cmd.exe (Windows paths cannot contain `"`).
 */
export function launcher(platform = process.platform, code) {
  if (platform === "win32") {
    return { command: code ?? "code.cmd", shell: true, quote: (a) => `"${a}"` };
  }
  return { command: code ?? "code", shell: false, quote: (a) => a };
}

export function launchArgs({ extension, workspace, runDir, port }) {
  return [
    "--new-window",
    "--disable-workspace-trust",
    "--skip-welcome",
    "--skip-release-notes",
    "--disable-extensions",
    `--user-data-dir=${path.join(runDir, "profile")}`,
    `--extensions-dir=${path.join(runDir, "extensions")}`,
    `--extensionDevelopmentPath=${path.resolve(extension)}`,
    `--remote-debugging-port=${port}`,
    path.resolve(workspace),
  ];
}

/** Wraps an expression so it runs against the document inside the webview's inner frame, bound as `d`. */
export function webviewExpression(expression) {
  return `(() => { const d = document.querySelector("iframe")?.contentDocument; if (!d) return undefined; return (${expression}); })()`;
}

/**
 * Webview targets, optionally only those of one extension. Both hosts put the extension id in the
 * target URL: desktop on `vscode-webview://`, browser-hosted on an `https://….vscode-cdn.net` origin.
 */
export function webviewTargets(targets, extensionId) {
  return targets.filter((t) => {
    if (t.type !== "iframe") return false;
    const id = URL.canParse(t.url) ? new URL(t.url).searchParams.get("extensionId") : null;
    return id !== null && (!extensionId || id.toLowerCase() === extensionId.toLowerCase());
  });
}

/** Where the downloaded VS Code server is kept between runs. */
export function userCacheDir(platform, env, home) {
  const name = "verify-vscode-extension";
  if (platform === "win32") return path.join(env.LOCALAPPDATA ?? path.join(home, "AppData", "Local"), name);
  if (platform === "darwin") return path.join(home, "Library", "Caches", name);
  return path.join(env.XDG_CACHE_HOME ?? path.join(home, ".cache"), name);
}

/** The installed server's own CLI, which installs extensions into a server data dir. */
export function serverCli(cacheDir, commit, platform) {
  return path.join(cacheDir, "serve-web", commit, "bin", platform === "win32" ? "code-server.cmd" : "code-server");
}

export function serveWebArgs({ webPort, tokenFile, serverDataDir, cliDataDir }) {
  return [
    "serve-web",
    "--port", String(webPort),
    "--connection-token-file", tokenFile,
    "--accept-server-license-terms",
    "--server-data-dir", serverDataDir,
    "--cli-data-dir", cliDataDir,
    "--disable-telemetry",
  ];
}

export function webUrl({ webPort, token, folder }) {
  const url = new URL(`http://127.0.0.1:${webPort}/`);
  url.searchParams.set("tkn", token);
  url.searchParams.set("folder", folder);
  return url.href;
}

/** Chrome or Chromium, in the order they are tried; `chrome` (from --chrome) replaces the list. */
export function chromeCandidates(platform, env, chrome) {
  if (chrome) return [chrome];
  if (platform === "win32") {
    return [env.PROGRAMFILES, env["PROGRAMFILES(X86)"], env.LOCALAPPDATA]
      .filter(Boolean)
      .map((base) => path.join(base, "Google", "Chrome", "Application", "chrome.exe"));
  }
  if (platform === "darwin") {
    return [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ];
  }
  return ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"];
}

export function chromeArgs({ port, profile, url }) {
  return [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "--window-size=1600,1000",
    "--no-first-run",
    "--no-default-browser-check",
    url,
  ];
}

/**
 * How to stop the server with everything it started. Killing only the launcher left the server it had
 * spawned running on Linux, reparented to PID 1. POSIX: the launcher is started detached, which makes
 * it a process-group leader, and the group is signalled. Windows: taskkill walks the tree.
 */
export function stopServerPlan(platform, pid) {
  if (platform === "win32") return { command: "taskkill", args: ["/PID", String(pid), "/T", "/F"] };
  return { group: -pid };
}

/** Browser-hosted runs keep what `close` and `install` need here, keyed by the DevTools port. */
export function stateFile(port, tmpdir = os.tmpdir()) {
  return path.join(tmpdir, `verify-vscode-extension-${port}.json`);
}

const NAMED_KEYS = { Enter: 13, Escape: 27, Tab: 9, Backspace: 8, Space: 32, ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40, Home: 36, End: 35, PageUp: 33, PageDown: 34 };
const MODIFIER_BITS = { Alt: 1, Ctrl: 2, Meta: 4, Shift: 8 };

/**
 * One CDP key event from a combo such as `Ctrl+K`, `Enter` or `a`. A plain character carries `text`,
 * which is what makes it type; with a modifier it is a shortcut and carries none.
 */
export function keyEvent(combo) {
  const parts = combo.split("+");
  const name = parts.pop();
  const modifiers = parts.reduce((m, p) => {
    if (!(p in MODIFIER_BITS)) throw new Error(`unknown modifier ${p} (${Object.keys(MODIFIER_BITS).join(", ")})`);
    return m | MODIFIER_BITS[p];
  }, 0);
  const char = /^[a-z0-9]$/i.test(name);
  if (!char && !(name in NAMED_KEYS)) {
    throw new Error(`unknown key ${name}: a letter, a digit, or one of ${Object.keys(NAMED_KEYS).join(", ")}`);
  }
  const key = name === "Space" ? " " : char ? name.toLowerCase() : name;
  const code = char ? (/\d/.test(name) ? `Digit${name}` : `Key${name.toUpperCase()}`) : name;
  const windowsVirtualKeyCode = char ? name.toUpperCase().charCodeAt(0) : NAMED_KEYS[name];
  const text = !modifiers && (char || name === "Space") ? key : undefined;
  return { key, code, windowsVirtualKeyCode, modifiers, text };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function json(port, route) {
  const res = await fetch(`http://127.0.0.1:${port}${route}`);
  return res.json();
}

async function reachable(port) {
  try {
    await json(port, "/json/version");
    return true;
  } catch {
    return false;
  }
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  };
  const ready = new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });
  const send = (method, params = {}) =>
    new Promise((resolve) => {
      const i = ++id;
      pending.set(i, resolve);
      ws.send(JSON.stringify({ id: i, method, params }));
    });
  return { ready, send, close: () => ws.close() };
}

async function evaluate(target, expression) {
  const c = connect(target.webSocketDebuggerUrl);
  await c.ready;
  const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  c.close();
  if (r.result?.exceptionDetails) {
    throw new Error(r.result.exceptionDetails.exception?.description ?? "the expression threw");
  }
  return r.result?.result?.value;
}

// The workbench is the page that renders `.monaco-workbench`: desktop serves it from vscode-file://,
// a browser-hosted VS Code from its server's own URL.
async function workbenchPage(port) {
  for (const t of (await json(port, "/json/list")).filter((t) => t.type === "page")) {
    if (await evaluate(t, `!!document.querySelector(".monaco-workbench")`).catch(() => false)) return t;
  }
  throw new Error(`no workbench page on port ${port}: run launch first`);
}

async function mouseClick(page, x, y) {
  const c = connect(page.webSocketDebuggerUrl);
  await c.ready;
  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await c.send("Input.dispatchMouseEvent", { type, x, y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1 });
  }
  c.close();
  return `clicked ${Math.round(x)},${Math.round(y)}`;
}

/** Clicks the center of the workbench element `expression` evaluates to. */
async function clickWorkbench(port, expression, what) {
  const page = await workbenchPage(port);
  const center = await evaluate(page, `(el => el && (b => [b.x + b.width / 2, b.y + b.height / 2])(el.getBoundingClientRect()))(${expression})`);
  if (!center) throw new Error(`not found: ${what}`);
  return mouseClick(page, center[0], center[1]);
}

function findExecutable(candidates) {
  const dirs = (process.env.PATH ?? "").split(path.delimiter).filter(Boolean);
  for (const c of candidates) {
    if (path.isAbsolute(c)) {
      if (fs.existsSync(c)) return c;
    } else {
      for (const dir of dirs) if (fs.existsSync(path.join(dir, c))) return path.join(dir, c);
    }
  }
  return undefined;
}

/** Runs a `.cmd` on Windows through cmd.exe, as Node requires, with each argument quoted. */
function runSync(exe, args) {
  const shell = process.platform === "win32" && /\.cmd$/i.test(exe);
  const r = spawnSync(shell ? `"${exe}"` : exe, shell ? args.map((a) => `"${a}"`) : args, { shell, encoding: "utf8", windowsHide: true });
  if (r.error) throw new Error(`could not run ${exe}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${exe} exited ${r.status}: ${(r.stderr || r.stdout).trim()}`);
  return r.stdout;
}

function codeCommit(code) {
  const { command, shell, quote } = launcher(process.platform, code);
  const r = spawnSync(command, [quote("--version")], { shell, encoding: "utf8", windowsHide: true });
  const commit = r.stdout?.split(/\r?\n/)[1]?.trim();
  if (!commit) throw new Error(`could not read the commit from \`${command} --version\``);
  return commit;
}

function stopServer(state) {
  const plan = stopServerPlan(process.platform, state.serverPid);
  try {
    if (plan.group) process.kill(plan.group, "SIGTERM");
    else spawnSync(plan.command, plan.args, { windowsHide: true });
  } catch (e) {
    if (e.code !== "ESRCH") throw e;
  }
}

async function answers(url) {
  try {
    return (await fetch(url, { redirect: "manual" })).status;
  } catch {
    return 0;
  }
}

async function waitForWorkbench(port, deadline) {
  while (Date.now() < deadline) {
    try {
      await workbenchPage(port);
      await sleep(4000); // the workbench page exists before extensions activate
      return;
    } catch {
      await sleep(1000);
    }
  }
  throw new Error(`no workbench on port ${port}`);
}

async function runPalette(port, text) {
  const page = await workbenchPage(port);
  const c = connect(page.webSocketDebuggerUrl);
  await c.ready;
  await c.send("Page.bringToFront");
  const mods = paletteModifiers();
  const key = (type, k, code, vk, modifiers = 0) =>
    c.send("Input.dispatchKeyEvent", { type, key: k, code, windowsVirtualKeyCode: vk, modifiers });
  await key("rawKeyDown", "p", "KeyP", 80, mods);
  await key("keyUp", "p", "KeyP", 80, mods);
  await sleep(800);
  await c.send("Input.insertText", { text });
  await sleep(800);
  await key("rawKeyDown", "Enter", "Enter", 13);
  await key("keyUp", "Enter", "Enter", 13);
  c.close();
  await sleep(1500);
}

/**
 * A browser-hosted workspace opens in Restricted Mode, which disables an extension that declares no
 * untrusted-workspace support. Writing the trust setting into the server's settings.json did not
 * change that; the trust editor's "Trust" button does.
 */
async function trustWorkspace(port) {
  const restricted = `!!document.querySelector('[id="status.workspaceTrust"]')`;
  if (!(await evaluate(await workbenchPage(port), restricted))) return;
  await runPalette(port, "Workspaces: Manage Workspace Trust");
  await clickWorkbench(port, `document.querySelector(".workspace-trust-editor .monaco-button")`, "the trust editor's Trust button");
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (!(await evaluate(await workbenchPage(port), restricted))) return;
    await sleep(500);
  }
  throw new Error("the workspace is still in Restricted Mode");
}

async function inWebview(port, expression, extensionId) {
  const views = webviewTargets(await json(port, "/json/list"), extensionId);
  if (views.length === 0) {
    throw new Error(
      extensionId
        ? `no webview from extension ${extensionId} is open (see the extensionId= values in \`targets\`)`
        : "no webview is open: open it first, e.g. with palette",
    );
  }
  for (const t of views) {
    const value = await evaluate(t, webviewExpression(expression));
    if (value !== undefined) return value;
  }
  throw new Error("no webview returned a value: does the expression return one?");
}

const print = (v) => console.log(typeof v === "string" ? v : JSON.stringify(v, null, 2));

async function main(argv) {
  const { positionals, options } = parseArgs(argv);
  const [command, ...args] = positionals;
  const port = Number(options.port ?? DEFAULT_PORT);
  const lit = (s) => JSON.stringify(s);

  switch (command) {
    case "launch": {
      if (!options.extension || !options.workspace) throw new Error("launch needs --extension and --workspace");
      if (await reachable(port)) throw new Error(`port ${port} is already in use: close that window or pass --port`);
      const runDir = path.resolve(options["run-dir"] ?? fs.mkdtempSync(path.join(os.tmpdir(), "vscode-verify-")));
      let workspace = options.workspace;
      if (options["copy-workspace"]) {
        workspace = path.join(runDir, "workspace");
        fs.cpSync(options.workspace, workspace, { recursive: true });
      }
      const { command: exe, shell, quote } = launcher(process.platform, options.code);
      const args = launchArgs({ extension: options.extension, workspace, runDir, port });
      const child = spawn(exe, args.map(quote), { shell, detached: true, stdio: "ignore", windowsHide: true });
      child.on("error", (e) => {
        console.error(`could not start ${exe}: ${e.message}`);
        process.exit(1);
      });
      child.unref();
      await waitForWorkbench(port, Date.now() + Number(options.timeout ?? 90) * 1000).catch(() => {
        throw new Error(`no window on port ${port} after ${options.timeout ?? 90}s`);
      });
      console.log(runDir);
      return;
    }
    case "launch-web": {
      if (!options.vsix || !options.workspace) throw new Error("launch-web needs --vsix and --workspace");
      const webPort = Number(options["web-port"] ?? DEFAULT_WEB_PORT);
      if (await reachable(port)) throw new Error(`port ${port} is already in use: close that instance or pass --port`);
      if (await answers(`http://127.0.0.1:${webPort}/`)) throw new Error(`port ${webPort} is already in use: pass --web-port`);
      const chrome = findExecutable(chromeCandidates(process.platform, process.env, options.chrome));
      if (!chrome) throw new Error("no Chrome or Chromium found: pass --chrome <exe>");
      const runDir = path.resolve(options["run-dir"] ?? fs.mkdtempSync(path.join(os.tmpdir(), "vscode-verify-")));
      let workspace = path.resolve(options.workspace);
      if (options["copy-workspace"]) {
        workspace = path.join(runDir, "workspace");
        fs.cpSync(options.workspace, workspace, { recursive: true });
      }
      const cacheDir = path.resolve(options["cache-dir"] ?? userCacheDir(process.platform, process.env, os.homedir()));
      const token = crypto.randomBytes(16).toString("hex");
      fs.writeFileSync(path.join(runDir, "token"), token);

      const { command: exe, shell, quote } = launcher(process.platform, options.code);
      const log = fs.openSync(path.join(runDir, "serve-web.log"), "a");
      const args = serveWebArgs({ webPort, tokenFile: path.join(runDir, "token"), serverDataDir: path.join(runDir, "server"), cliDataDir: cacheDir });
      // detached: on POSIX the launcher leads a new process group, which is what stopServer signals.
      const server = spawn(exe, args.map(quote), { shell, detached: true, stdio: ["ignore", log, log], windowsHide: true });
      server.unref();
      const state = { runDir, serverPid: server.pid, webPort, cli: serverCli(cacheDir, codeCommit(options.code), process.platform), serverDataDir: path.join(runDir, "server") };
      fs.writeFileSync(stateFile(port), JSON.stringify(state, null, 2));
      try {
        // The first request starts the server's download (it answered 202 while downloading), and
        // only a 302 meant it was running, with the files the install below needs.
        const deadline = Date.now() + Number(options.timeout ?? 180) * 1000;
        while ((await answers(`http://127.0.0.1:${webPort}/?tkn=${token}`)) !== 302) {
          if (Date.now() > deadline) throw new Error(`serve-web did not come up; see ${path.join(runDir, "serve-web.log")}`);
          await sleep(1000);
        }
        runSync(state.cli, ["--server-data-dir", state.serverDataDir, "--install-extension", path.resolve(options.vsix)]);
        const browser = spawn(chrome, chromeArgs({ port, profile: path.join(runDir, "chrome"), url: webUrl({ webPort, token, folder: workspace }) }), {
          detached: true,
          stdio: "ignore",
          windowsHide: true,
        });
        browser.unref();
        await waitForWorkbench(port, deadline);
        await trustWorkspace(port);
      } catch (e) {
        if (await reachable(port)) {
          const c = connect((await json(port, "/json/version")).webSocketDebuggerUrl);
          await c.ready;
          c.send("Browser.close");
        }
        stopServer(state);
        fs.rmSync(stateFile(port), { force: true });
        throw e;
      }
      console.log(runDir);
      return;
    }
    case "install": {
      if (!options.vsix) throw new Error("install needs --vsix");
      if (!fs.existsSync(stateFile(port))) throw new Error(`no browser-hosted instance on port ${port}: install is for launch-web`);
      const state = JSON.parse(fs.readFileSync(stateFile(port), "utf8"));
      runSync(state.cli, ["--server-data-dir", state.serverDataDir, "--install-extension", path.resolve(options.vsix), "--force"]);
      await evaluate(await workbenchPage(port), "location.reload()");
      await sleep(2000);
      await waitForWorkbench(port, Date.now() + 60_000);
      console.log("installed and reloaded");
      return;
    }
    case "close": {
      if (await reachable(port)) {
        const { webSocketDebuggerUrl } = await json(port, "/json/version");
        const c = connect(webSocketDebuggerUrl);
        await c.ready;
        c.send("Browser.close");
        const deadline = Date.now() + 30_000;
        while (Date.now() < deadline && (await reachable(port))) await sleep(500);
        if (await reachable(port)) throw new Error("the window is still up after 30s");
      }
      if (fs.existsSync(stateFile(port))) {
        const state = JSON.parse(fs.readFileSync(stateFile(port), "utf8"));
        stopServer(state);
        const deadline = Date.now() + 30_000;
        while (Date.now() < deadline && (await answers(`http://127.0.0.1:${state.webPort}/`))) await sleep(500);
        if (await answers(`http://127.0.0.1:${state.webPort}/`)) throw new Error(`serve-web still answers on ${state.webPort} after 30s`);
        fs.rmSync(stateFile(port), { force: true });
      }
      console.log("closed");
      return;
    }
    case "targets": {
      for (const t of await json(port, "/json/list")) console.log(`${t.type} | ${t.title.slice(0, 50)} | ${t.url}`);
      return;
    }
    case "palette": {
      await runPalette(port, args.join(" "));
      return;
    }
    case "click-link":
    case "click-app": {
      // A real mouse click, so VS Code's own listeners see what a user's click produces: the element's
      // box in the extension's frame, plus that frame's offset in the host frame, plus the host
      // frame's offset in the workbench (the webview element whose src carries the target's id).
      const element =
        command === "click-link"
          ? `[...d.querySelectorAll("a")].find(a => a.getAttribute("href") === ${lit(args[0])})`
          : `d.querySelector(${lit(args[0])})`;
      const views = webviewTargets(await json(port, "/json/list"), options["extension-id"]);
      for (const t of views) {
        const box = await evaluate(
          t,
          webviewExpression(
            `(a => a ? (f => (b => [f.x + b.x + Math.min(12, b.width / 2), f.y + b.y + b.height / 2])(a.getBoundingClientRect()))(document.querySelector("iframe").getBoundingClientRect()) : null)(${element})`,
          ),
        );
        if (!box) continue;
        const id = new URL(t.url).searchParams.get("id") ?? "";
        const page = await workbenchPage(port);
        const frame = await evaluate(
          page,
          `(f => f && [f.getBoundingClientRect().x, f.getBoundingClientRect().y])([...document.querySelectorAll("iframe.webview")].find(f => new URL(f.src).searchParams.get("id") === ${lit(id)}))`,
        );
        if (!frame) throw new Error("found the element, but not the workbench element hosting its webview");
        print(await mouseClick(page, frame[0] + box[0], frame[1] + box[1]));
        return;
      }
      if (!views.length) throw new Error("no webview is open: open it first, e.g. with palette");
      throw new Error(command === "click-link" ? `no link with href ${args[0]}` : `nothing in the webview matches ${args[0]}`);
    }
    case "click-row":
    case "expand-row": {
      // Matched on the label the row displays, not its aria-label, which VS Code fills from the
      // item's tooltip when it has one.
      const [container, label] = args;
      const scope = JSON.stringify(`workbench.view.extension.${container}`);
      const row = `[...document.querySelectorAll('[id=' + ${lit(scope)} + '] .monaco-list-row')].find(r => r.querySelector(".label-name")?.textContent === ${lit(label)})`;
      print(
        await clickWorkbench(
          port,
          command === "click-row" ? row : `${row}?.querySelector(".monaco-tl-twistie")`,
          `row "${label}" in ${container} (is the container open, and the row's folder expanded?)`,
        ),
      );
      return;
    }
    case "key":
    case "type": {
      // Input goes wherever focus is, as a user's would: click into a webview first to reach it.
      const page = await workbenchPage(port);
      const c = connect(page.webSocketDebuggerUrl);
      await c.ready;
      if (command === "type") {
        await c.send("Input.insertText", { text: args.join(" ") });
      } else {
        const e = keyEvent(args[0]);
        await c.send("Input.dispatchKeyEvent", { type: e.text ? "keyDown" : "rawKeyDown", ...e });
        await c.send("Input.dispatchKeyEvent", { type: "keyUp", ...e, text: undefined });
      }
      c.close();
      print(command === "key" ? `pressed ${args[0]}` : `typed ${args.join(" ")}`);
      return;
    }
    case "click": {
      print(await clickWorkbench(port, `document.querySelector(${lit(args[0])})`, args[0]));
      return;
    }
    case "fill": {
      const [selector, value] = args;
      print(
        await inWebview(
          port,
          `(i => { if (!i) return "nothing matches " + ${lit(selector)}; const w = d.defaultView; Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype, "value").set.call(i, ${lit(value)}); i.dispatchEvent(new w.Event("input", { bubbles: true })); return "filled"; })(d.querySelector(${lit(selector)}))`,
          options["extension-id"],
        ),
      );
      return;
    }
    case "rows": {
      print(
        await inWebview(
          port,
          `[...d.querySelectorAll(${lit(args[0])})].map(e => e.innerText.replace(/\\s+/g, " ").trim()).join("\\n")`,
          options["extension-id"],
        ),
      );
      return;
    }
    case "tree-rows": {
      const container = `workbench.view.extension.${args[0]}`;
      print(
        await evaluate(
          await workbenchPage(port),
          `[...document.querySelectorAll('[id=' + ${lit(JSON.stringify(container))} + '] .monaco-list-row')].map(r => [r.querySelector(".label-name")?.textContent, r.querySelector(".label-description")?.textContent].filter(Boolean).join("  ")).join("\\n")`,
        ),
      );
      return;
    }
    case "webview":
    case "workbench": {
      if (!options.file) throw new Error(`${command} needs --file <js file>`);
      const expression = fs.readFileSync(options.file, "utf8").trim();
      print(
        command === "webview"
          ? await inWebview(port, expression, options["extension-id"])
          : await evaluate(await workbenchPage(port), expression),
      );
      return;
    }
    case "shot": {
      const page = await workbenchPage(port);
      const c = connect(page.webSocketDebuggerUrl);
      await c.ready;
      const r = await c.send("Page.captureScreenshot", { format: "png" });
      c.close();
      fs.writeFileSync(args[0], Buffer.from(r.result.data, "base64"));
      console.log(path.resolve(args[0]));
      return;
    }
    case undefined:
    case "help":
      console.log(USAGE);
      return;
    default:
      throw new Error(`unknown command: ${command}\n\n${USAGE}`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(
    () => process.exit(0),
    (e) => {
      console.error(e.message);
      process.exit(1);
    },
  );
}
