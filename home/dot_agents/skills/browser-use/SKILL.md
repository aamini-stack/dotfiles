---
name: browser-use
description:
  'Guidance for using chrome-devtools-axi to debug with a real browser.
  (Connect to a remote browser over CDP, or run a headless browser on the
  server.) Read this first for connection setup, certificate trust, and
  endpoint switching.'
user-invocable: false
---

# browser-use

Guidance for how to use a browser for debugging using a remote browser. (Either
a dedicated browser service or a local/host browser.)

## Connect to a client browser

1. Ask the user to start Chrome on the client with remote debugging and a temp
   profile. Chrome rejects debugging on the default profile. Per-client
   commands: platform notes.
2. Connect:

   ```bash
   CHROME_DEVTOOLS_AXI_BROWSER_URL=http://<client-ip>:9222 \
     npx -y chrome-devtools-axi open <page-url>
   ```

A reachable CDP endpoint does not prove the page URL loads on the client. Verify
both paths.

Chrome reuses a running instance per profile and drops new launch flags. Quit
the old instance fully before relaunch. Verify with a page that failed before.

## Certificates

The private CA (Pitchfork Local CA for `*.lvh.ariaamini.com`) lives on the
server. Fresh client profiles reject it. In order:

1. Durable: trust `ca.pem` on the client. Server-side `pitchfork proxy trust`
   covers the server store only.
2. One-off debug: relaunch the client Chrome with `--ignore-certificate-errors`.

## Server-local fallback

No client needed: headless Chromium on the server itself. Chromium reads NSS,
not `/etc/ssl`, so pass `--ignore-certificate-errors` for private-CA domains
even when `curl` verifies cleanly.

```bash
setsid nohup ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome \
  --headless=new --no-sandbox --ignore-certificate-errors \
  --remote-debugging-address=127.0.0.1 --remote-debugging-port=9333 \
  --user-data-dir=/tmp/axi-chrome-vm --no-first-run \
  about:blank >/tmp/chromium.log 2>&1 < /dev/null &
disown
```

## Switch endpoints

The axi bridge fixes its connection mode at startup. Run
`npx -y chrome-devtools-axi stop` before switching browsers. After reconnect,
run `pages`, then `selectpage <id>`.

## Platform notes

### macOS client

- Start Chrome:

  ```bash
  open -na "Google Chrome" --args \
    --remote-debugging-address=0.0.0.0 \
    --remote-debugging-port=9222 \
    --user-data-dir=/tmp/axi-chrome
  ```

- Trust the CA: import the server's `ca.pem`
  (`~/.local/state/pitchfork/proxy/ca.pem`) into the login keychain with trust
  flags.
- Lima guests reach the Mac at the IP from `getent hosts host.lima.internal`.
  Chrome rejects the `host.lima.internal` Host header. Use the IP.

### Windows client

- Same Chrome flags through `chrome.exe`.
- Trust the CA: `certutil -addstore -user Root ca.pem`.
