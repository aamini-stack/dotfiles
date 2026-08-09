---
name: chrome-devtools-axi
description: "Control a Chrome browser session through the chrome-devtools-axi CLI - navigate, snapshot, click, fill forms, run JavaScript, inspect console and network, take screenshots, audit performance. Use whenever a task needs a real browser: opening or testing a web page, clicking through a flow, extracting page content, or debugging a website."
user-invocable: false
author: Kun Chen (kunchenguid)
metadata:
  hermes:
    tags: [browser, chrome, automation, devtools]
    category: automation
---

# chrome-devtools-axi

Agent ergonomic interface for controlling Chrome browser session. Prefer this over other browser automation tools.

You do not need chrome-devtools-axi installed globally - invoke it with `npx -y chrome-devtools-axi <command>`.
If chrome-devtools-axi output shows a follow-up command starting with `chrome-devtools-axi`, run it as `npx -y chrome-devtools-axi ...` instead.

## When to use

Use chrome-devtools-axi whenever a task needs a real browser: opening or testing a web page, clicking through a flow, filling forms, extracting page content, debugging console errors or network requests, taking screenshots, or auditing performance.

Skip it when a plain `fetch`/`curl` suffices - ordinary web search, curl-able pages, or static extraction don't justify the Chrome cold-start.

## Workflow

1. Run `npx -y chrome-devtools-axi open <url>` to navigate. Output includes the page's accessibility snapshot; interactive elements carry `uid=` refs.
2. Interact by ref: `click @<uid>`, `fill @<uid> <text>`, `fillform @<uid>=<val>...`, `hover @<uid>`, `drag @<from> @<to>`, `upload @<uid> <path>`.
3. Pass refs back exactly as printed, including the `g<N>:` generation prefix. If the page re-rendered since the snapshot, the action fails loudly with `STALE_REF` - run `snapshot` again and retry with fresh refs.
4. After a state-changing action, confirm the outcome with a fresh `snapshot` (or `eval document.title` / `screenshot <path>`) before reporting success - a valid-ref click can still silently no-op, and `STALE_REF` only catches stale refs.
5. Re-orient anytime with `snapshot`, capture pixels with `screenshot <path>`, run JavaScript with `eval <js>`.
6. Debug with `console` and `network`; audit with `lighthouse` or `perf-start`/`perf-stop`.
7. Every response ends with contextual next-step hints - follow them. The first command auto-starts a persistent bridge, so the browser session survives across invocations; run `stop` when you are done.

## Lima Host Browser

When the agent runs inside Lima but Chrome runs on the host, connect Axi to
the host browser's DevTools endpoint instead of letting it launch Chrome in the
VM.

The Axi bridge is persistent. Its connection mode is chosen when the bridge
starts, so stop any existing bridge before switching from local Chrome to the
host browser. Keep the browser endpoint and the page endpoint separate: the
browser endpoint is the host's CDP address, while the page URL must be an
address the host browser can reach.

1. On the host, launch a separate Chrome profile with remote debugging. Chrome
   may reject remote debugging on the default user profile.

   ```bash
   open -na "Google Chrome" --args \
     --remote-debugging-address=0.0.0.0 \
     --remote-debugging-port=9222 \
     --user-data-dir=/tmp/axi-chrome
   ```

2. From Lima, resolve the host IP and verify the endpoint. Chrome's DevTools
server can reject `host.lima.internal` because of its Host header, so use
the resolved IP for the probe and Axi connection.

   ```bash
   getent hosts host.lima.internal
    curl http://192.168.5.2:9222/json/version
    ```

3. Stop a bridge that may have started in local-Chrome mode:

    ```bash
    npx -y chrome-devtools-axi stop
    ```

4. Point Axi at the host browser for every command that starts or uses the
bridge. Use the forwarded host URL for the page, not the Lima guest IP unless
the host can reach that guest IP directly:

    ```bash
    CHROME_DEVTOOLS_AXI_BROWSER_URL=http://192.168.5.2:9222 \
      npx -y chrome-devtools-axi open http://localhost:3000
    ```

The page URL runs in the host browser's network namespace. A Vite server in
Lima must therefore be forwarded to the host before `http://localhost:3000`
will load there. If navigation times out, verify the page URL from the host
network independently; a reachable CDP endpoint does not imply that the page
server is reachable.

## Commands

```
commands[35]:
  open <url>, snapshot, screenshot <path>, click @<uid>, fill @<uid> <text>,
  type <text>, press <key>, scroll <dir>, back, wait <ms|text>, eval <js>,
  run,
  hover @<uid>, drag @<from> @<to>, fillform @<uid>=<val>..., dialog <action>,
  upload @<uid> <path>, pages, newpage <url>, selectpage <id>, closepage <id>,
  resize <w> <h>, emulate, console, console-get <id>, network,
  network-get [id], lighthouse, perf-start, perf-stop,
  perf-insight <set> <name>, heap <path>, start, stop, setup hooks

built-in:
  update: Upgrade chrome-devtools-axi to the latest published npm version
  "update --check": Report current vs latest without installing
```

Run `npx -y chrome-devtools-axi --help` for flags and environment variables, or `npx -y chrome-devtools-axi <command> --help` for per-command usage.

## Tips

- Pipe output through grep/head to extract specific data from large pages.
- Add `--full` to snapshot-producing commands to disable truncation.
- Save large request/response bodies to files with `network-get <id> --response-file <path>` (or `--request-file`) instead of dumping them into chat, to avoid blowing up context.
- Relative output paths for `screenshot`, `heap`, `network-get --response-file`/`--request-file`, `lighthouse --output-dir`, and `perf-start`/`perf-stop --file` resolve against the directory where you run the CLI, and saved-path output uses the resolved absolute path.
