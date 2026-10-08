// Run with: node --test tests/test_vscode_cdp.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import {
  chromeArgs,
  chromeCandidates,
  keyEvent,
  launchArgs,
  launcher,
  paletteModifiers,
  parseArgs,
  serveWebArgs,
  serverCli,
  stateFile,
  stopServerPlan,
  userCacheDir,
  webUrl,
  webviewExpression,
  webviewTargets,
} from "../scripts/vscode_cdp.mjs";

test("options take a value, flags do not, the rest are positionals", () => {
  assert.deepEqual(parseArgs(["fill", "input", "a b", "--port", "9400", "--copy-workspace"]), {
    positionals: ["fill", "input", "a b"],
    options: { port: "9400", "copy-workspace": true },
  });
  assert.throws(() => parseArgs(["launch", "--extension"]), /--extension needs a value/);
});

test("the palette is Cmd+Shift+P on macOS and Ctrl+Shift+P elsewhere", () => {
  assert.equal(paletteModifiers("darwin"), 4 | 8);
  assert.equal(paletteModifiers("linux"), 2 | 8);
  assert.equal(paletteModifiers("win32"), 2 | 8);
});

test("Windows starts code.cmd through a shell with every argument quoted", () => {
  const win = launcher("win32");
  assert.equal(win.command, "code.cmd");
  assert.equal(win.shell, true);
  assert.equal(win.quote("C:\\Program Files\\x"), '"C:\\Program Files\\x"');
  const unix = launcher("linux");
  assert.deepEqual([unix.command, unix.shell, unix.quote("/a b")], ["code", false, "/a b"]);
  assert.equal(launcher("darwin", "/opt/code").command, "/opt/code");
});

test("launch paths are absolute, since a relative extension path is silently ignored", () => {
  const args = launchArgs({ extension: "ext", workspace: "ws", runDir: path.resolve("run"), port: 9333 });
  const dev = args.find((a) => a.startsWith("--extensionDevelopmentPath="));
  assert.ok(path.isAbsolute(dev.split("=")[1]), dev);
  assert.ok(path.isAbsolute(args.at(-1)), args.at(-1));
  assert.ok(args.includes("--remote-debugging-port=9333"));
  assert.ok(args.includes(`--user-data-dir=${path.join(path.resolve("run"), "profile")}`));
});

test("a webview expression runs against the inner frame's document", () => {
  const expr = webviewExpression("d.title");
  assert.match(expr, /document\.querySelector\("iframe"\)\?\.contentDocument/);
  assert.match(expr, /return \(d\.title\)/);
});

test("webview targets are filtered by the extension id in their URL", () => {
  const t = (id) => ({ type: "iframe", url: `vscode-webview://abc/index.html?id=1&extensionId=${id}&purpose=webviewView` });
  const targets = [t("pub.one"), t("pub.two"), { type: "page", url: "vscode-file://workbench.html" }];
  assert.equal(webviewTargets(targets).length, 2);
  assert.deepEqual(webviewTargets(targets, "PUB.two").map((x) => x.url), [targets[1].url]);
});

test("a browser-hosted webview is found by the same extension id, on its https origin", () => {
  const web = {
    type: "iframe",
    url: "https://abc.vscode-cdn.net/stable/0123/out/vs/workbench/contrib/webview/browser/pre/index.html?id=1&extensionId=pub.one",
  };
  const other = { type: "iframe", url: "https://example.com/embed" };
  assert.deepEqual(webviewTargets([web, other]), [web]);
  assert.deepEqual(webviewTargets([web, other], "pub.one"), [web]);
});

test("the server cache lives in each platform's user cache directory", () => {
  assert.equal(userCacheDir("linux", {}, "/home/u"), path.join("/home/u", ".cache", "verify-vscode-extension"));
  assert.equal(userCacheDir("linux", { XDG_CACHE_HOME: "/x" }, "/home/u"), path.join("/x", "verify-vscode-extension"));
  assert.equal(userCacheDir("darwin", {}, "/Users/u"), path.join("/Users/u", "Library", "Caches", "verify-vscode-extension"));
  assert.equal(
    userCacheDir("win32", { LOCALAPPDATA: "C:\\Users\\u\\AppData\\Local" }, "C:\\Users\\u"),
    path.join("C:\\Users\\u\\AppData\\Local", "verify-vscode-extension"),
  );
});

test("the server's own CLI is code-server, a .cmd on Windows", () => {
  assert.equal(serverCli("/c", "abc", "linux"), path.join("/c", "serve-web", "abc", "bin", "code-server"));
  assert.equal(serverCli("/c", "abc", "win32"), path.join("/c", "serve-web", "abc", "bin", "code-server.cmd"));
});

test("serve-web is started with a token file, its own data dir, and the shared download cache", () => {
  const args = serveWebArgs({ webPort: 8123, tokenFile: "/r/token", serverDataDir: "/r/server", cliDataDir: "/c" });
  assert.equal(args[0], "serve-web");
  for (const pair of [["--port", "8123"], ["--connection-token-file", "/r/token"], ["--server-data-dir", "/r/server"], ["--cli-data-dir", "/c"]]) {
    assert.equal(args[args.indexOf(pair[0]) + 1], pair[1], pair[0]);
  }
  assert.ok(args.includes("--accept-server-license-terms"));
  assert.ok(!args.includes("--without-connection-token"));
});

test("the web URL carries the token and the folder, encoded", () => {
  const url = new URL(webUrl({ webPort: 8123, token: "t0k", folder: "/tmp/a b/ws" }));
  assert.equal(url.host, "127.0.0.1:8123");
  assert.equal(url.searchParams.get("tkn"), "t0k");
  assert.equal(url.searchParams.get("folder"), "/tmp/a b/ws");
});

test("Chrome is looked for where each platform installs it, and --chrome wins", () => {
  assert.deepEqual(chromeCandidates("linux", {}, "/opt/chrome"), ["/opt/chrome"]);
  assert.ok(chromeCandidates("linux", {}).includes("google-chrome-stable"));
  assert.ok(chromeCandidates("linux", {}).includes("chromium"));
  assert.ok(chromeCandidates("darwin", {}).includes("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"));
  const win = chromeCandidates("win32", { PROGRAMFILES: "C:\\PF", LOCALAPPDATA: "C:\\L" });
  assert.ok(win.includes(path.join("C:\\PF", "Google", "Chrome", "Application", "chrome.exe")));
  assert.ok(win.includes(path.join("C:\\L", "Google", "Chrome", "Application", "chrome.exe")));
});

test("Chrome runs headless, with its own profile and DevTools port", () => {
  const args = chromeArgs({ port: 9334, profile: "/r/chrome", url: "http://x/" });
  assert.ok(args.includes("--headless=new"));
  assert.ok(args.includes("--remote-debugging-port=9334"));
  assert.ok(args.includes("--user-data-dir=/r/chrome"));
  assert.equal(args.at(-1), "http://x/");
});

test("stopping the server takes its whole tree: a process group on POSIX, taskkill /T on Windows", () => {
  assert.deepEqual(stopServerPlan("linux", 42), { group: -42 });
  assert.deepEqual(stopServerPlan("darwin", 42), { group: -42 });
  assert.deepEqual(stopServerPlan("win32", 42), { command: "taskkill", args: ["/PID", "42", "/T", "/F"] });
});

test("web state is kept per DevTools port", () => {
  assert.equal(stateFile(9334, "/tmp"), path.join("/tmp", "verify-vscode-extension-9334.json"));
});

test("a key combo becomes one CDP key event: modifiers as bits, a plain character carries text", () => {
  assert.deepEqual(keyEvent("Ctrl+K"), { key: "k", code: "KeyK", windowsVirtualKeyCode: 75, modifiers: 2, text: undefined });
  assert.deepEqual(keyEvent("a"), { key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 0, text: "a" });
  assert.deepEqual(keyEvent("Meta+Shift+P"), { key: "p", code: "KeyP", windowsVirtualKeyCode: 80, modifiers: 4 | 8, text: undefined });
  assert.deepEqual(keyEvent("7"), { key: "7", code: "Digit7", windowsVirtualKeyCode: 55, modifiers: 0, text: "7" });
  assert.deepEqual(keyEvent("Enter"), { key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, modifiers: 0, text: undefined });
  assert.deepEqual(keyEvent("Space"), { key: " ", code: "Space", windowsVirtualKeyCode: 32, modifiers: 0, text: " " });
  assert.throws(() => keyEvent("Hyper+K"), /unknown modifier Hyper/);
  assert.throws(() => keyEvent("F13"), /unknown key F13/);
});
