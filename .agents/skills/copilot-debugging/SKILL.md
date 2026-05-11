---
name: copilot-debugging
description:
  Debug Azure Copilot HTTP plugins end-to-end in a real Azure Portal/Copilot
  browser session using Playwriter direct CDP, SideLoad scoped conversations,
  network traces, and service logs.
---

# Copilot Plugin Debugging

Use this skill to validate Azure Copilot HTTP plugins against the real Azure
Portal Copilot client. Prefer this over curl or synthetic tests when debugging
plugin routing, scoped conversations, confirmation cards, LRO polling, auth, or
client/service mismatches.

## Non-Negotiables

- Load the `playwriter` skill and run `playwriter skill` before browser work.
- Use Playwriter direct CDP for Azure Portal Copilot. Extension mode misses
  cross-origin sandbox frames used by Copilot and SideLoad.
- Use a temporary debug Edge profile.
- Never print bearer tokens, DirectLine tokens, or raw authorization attachment
  contents.
- Do not stop at `Sorry, I can't help with that. Please try something else.`
  Treat it as a prompt/registration/target-selection failure and keep tracing.
- Do not use the lower `CopilotTopActions` SideLoad component for plugin tests.
  It can default to `ArgStorage` and launch the query/storage agent.

## CDP Setup

Print this block to the user before starting a Portal Copilot session.

```powershell
# Launch Edge with CDP from Windows PowerShell.
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"

# Fallback path if needed.
& "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"

# Verify Edge is listening on Windows.
Invoke-RestMethod http://127.0.0.1:9222/json/version

# If the agent runs in WSL/Linux, expose CDP to WSL.
# Run PowerShell as Administrator.
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9223 connectaddress=127.0.0.1 connectport=9222
New-NetFirewallRule -DisplayName "Edge CDP from WSL" -Direction Inbound -LocalPort 9223 -Protocol TCP -Action Allow
```

Verify from WSL/Linux:

```bash
curl -sS --max-time 5 "http://$(ip route | awk '/default/ {print $3}'):9223/json/version"
curl -sS --max-time 5 "http://$(ip route | awk '/default/ {print $3}'):9223/json/list"
```

Start Playwriter with the WSL-reachable browser WebSocket URL, not the
Windows-local `127.0.0.1:9222` URL:

```bash
playwriter session new --direct ws://<wsl-gateway>:9223/devtools/browser/<browser-id>
```

## Portal URL

Use RC Portal with Copilot, DevUI, canary traffic, plugin store, and declarative
HTTP plugin flights enabled:

```text
https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.AzCopilot_ArgQueryGenerator_plugin=15.0&exp.AzCopilot_ArgQueryRunner_plugin=15.0&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&Microsoft_Azure_Copilot_clientoptimizations=false&feature.customportal=false&feature.canmodifyextensions=true#view/Microsoft_Azure_Copilot/SideLoad.ReactView
```

If Portal redirects to `/auth/login/`, wait 10-20 seconds and retry the Portal
URL once in the same authenticated page/profile before asking the user to sign
in. Fresh debug profiles and new tabs can briefly show `/auth/login/` even when
the user already completed sign-in. If the retry still lands on `/auth/login/`,
ask the user to finish sign-in in the debug Edge window, then navigate to the
same URL again.

If you need a fresh SideLoad blade instance, add any cache-busting query
parameter before the `#view/...` fragment, not after it. Appending text after
the hash changes the blade name, for example `SideLoad.ReactView&fresh=...`, and
Portal fails with `ErrorLoadingExtensionAndDefinition` and
`Blade name is invalid identifier`.

## Working E2E Flow

1. Connect to Edge with direct CDP and select the Portal page.
2. Load the Portal URL above.
   Use `playwriter -s <session> --timeout 120000 -e ...` for Portal loads,
   login retries, and long Copilot waits. The Playwriter CLI execution default
   can time out before an otherwise healthy Portal retry completes.
3. Inspect `/json/list` and identify the active SideLoad iframe by text:
   `Plugin & Agent Test`, `Scoped Conversations`, `Register`, and `monaco === true`.
4. Use one SideLoad iframe for both manifest registration and scoped submit.
5. If `Register` is already disabled before a new manifest registration, reload
   Portal and use a fresh SideLoad iframe.
6. Paste the full manifest into Monaco, wait for markers, and click `Register`
   only when markers are empty and `Register` is enabled. Preserve the manifest
   exactly; do not inline it into a single-quoted shell command because the Lua
   script contains single quotes.
7. Switch to `Scoped Conversations` in that same iframe.
8. Fill only the upper API form:
   `Competency = BicepDeploymentDebug` and the working prompt below.
9. Click the upper `Submit` button. Do not click `Open Copilot sidecar`.
10. Inspect all Portal sandbox iframes and choose the Copilot iframe by live
   text, not by newest target ID. The newest sandbox iframe can be blank while
   an older sandbox iframe contains the Copilot sidecar.
11. Inspect the Copilot iframe. It must show the exact prompt and the activity
   `Deploy built-in Bicep debug sample and request confirmation`.
12. Approve the confirmation card.
13. Wait for LRO output. A successful run shows `Deployment accepted by ARM`,
   `rg-copilot-bicep-debug - Succeeded`, and `Deployment succeeded!`.

## Working Bicep Debug Manifest

This manifest was validated against the real RC Portal Copilot client on
2026-05-11. It avoids putting Bicep source in the user prompt. The HTTP plugin
Lua script supplies the built-in sample files, which avoids model refusal before
tool selection.

The sample intentionally uses a valid multi-file Bicep module layout with
VM-shaped resources and an invalid VM size. This should compile, submit to ARM,
and then exercise deployment failure diagnostics instead of stopping at model
routing or Bicep syntax errors.

Use the adjacent file:

```text
bicep-deployment-debug.manifest.json
```

Paste that entire JSON object into the SideLoad Monaco editor. Prefer reading
the file from Node or using a quoted heredoc and setting Monaco directly. Do not
hand-build or shell-embed the JSON in a `playwriter -e '...'` one-liner; shell
quoting can strip Lua single quotes and produce a registered plugin that routes
but fails at tool execution.

After pasting, compare Monaco's current value to the file when possible. The Lua
script must still contain strings such as `'copilot-bicep-debug'`,
`'subscription'`, and `'eastus'`.

## Working Prompt

Use a real selected subscription ID. Do not embed Bicep source, fenced code, raw
JSON tool arguments, or numbered source lines in the prompt.

If the user does not provide a subscription, use an explicitly selected Portal
subscription. If you need a fallback and Azure CLI is logged in as the same
user, `az account show --query id -o tsv` is a reasonable source for the
default subscription. Do not depend on a browser `fetch` to
`https://management.azure.com/subscriptions`; the Portal page can return `401`
for that direct fetch even when Portal itself is authenticated.

```text
Deploy the built-in Bicep debug sample to subscription <subscription-id> in eastus. Use deployment label copilot-bicep-debug. Show the deployment confirmation first.
```

Expected confirmation card text:

```text
Are you sure you want to deploy this Bicep configuration?

Subscription: <subscription-id>
Location: eastus
Files: 2 file(s) - main.bicep, vm.bicep

Approve
Deny
```

Expected successful approved output:

```text
Compiling bicep templates...
Submitting deployment to ARM...
Deployment accepted by ARM.
rg-copilot-bicep-debug - Succeeded
Deployment succeeded!
```

## SideLoad Target Discipline

- Match targets by live text and state, never by stored target ID.
- Portal may keep stale SideLoad and Copilot iframes alive after reloads.
- Register and submit from the same verified SideLoad iframe.
- After submitting, inspect iframe contents and choose the Copilot sidecar by
  evidence: exact prompt text, `Agent has been registered`,
  `Plugin has been registered`, activity text, confirmation card, or final
  deployment output.
- If Monaco content changes but `Register` remains disabled, the target is
  post-registration locked. Reload Portal and use a fresh SideLoad iframe.
- If a retry shows old manifest behavior after a fresh registration, suspect a
  stale Copilot sidecar or stale SideLoad target. Close old Copilot sidecars,
  reload Portal, use a fresh SideLoad iframe, and verify the confirmation card
  reflects the current manifest before approving.
- If the sidecar shows an `ArgStorage` prompt such as `Get a list of all storage
  accounts in westus`, you clicked the lower `CopilotTopActions` path. Close the
  Copilot sidecar and use the upper API scoped form only.

## Browser Inspection Helpers

List pages:

```bash
playwriter -s <session> -e 'console.log(JSON.stringify(browser.contexts().map((c, ci) => ({ context: ci, pages: c.pages().map((p, pi) => ({ page: pi, title: p.title(), url: p.url() })) })), null, 2))'
```

Observe Portal:

```bash
playwriter -s <session> -e 'state.page = context.pages().find((p) => p.url().includes("portal.azure.com")) ?? context.pages()[0]; console.log("URL:", state.page.url()); console.log(await snapshot({ page: state.page, showDiffSinceLastCall: false }));'
```

Inspect CDP targets:

```bash
curl -sS --max-time 5 "http://$(ip route | awk '/default/ {print $3}'):9223/json/list"
```

Raw iframe evaluation pattern:

```bash
node <<'NODE'
const ws = "ws://<gateway>:9223/devtools/page/<target-id>"
const socket = new WebSocket(ws)
let id = 0
const pending = new Map()
socket.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg)
    pending.delete(msg.id)
  }
}
function send(method, params = {}) {
  return new Promise((resolve) => {
    const mid = ++id
    pending.set(mid, resolve)
    socket.send(JSON.stringify({ id: mid, method, params }))
  })
}
socket.onopen = async () => {
  await send("Runtime.enable")
  const expression = `JSON.stringify({
    text: document.body.innerText,
    buttons: [...document.querySelectorAll("button")].map((b, i) => ({ i, text: b.innerText, disabled: b.disabled })),
    inputs: [...document.querySelectorAll("input,textarea")].map((e, i) => ({ i, tag: e.tagName, value: e.value, placeholder: e.placeholder })),
    monaco: !!globalThis.monaco,
  })`
  const res = await send("Runtime.evaluate", { returnByValue: true, expression })
  console.log(res.result.result.value)
  socket.close()
}
NODE
```

Paste manifest into Monaco via direct CDP without shell-quoting damage:

```bash
node <<'NODE'
const fs = require('node:fs')
const manifest = fs.readFileSync('/home/ariaamini/.agents/skills/copilot-debugging/bicep-deployment-debug.manifest.json', 'utf8')
const ws = 'ws://<gateway>:9223/devtools/page/<sideload-target-id>'
const socket = new WebSocket(ws)
let id = 0
const pending = new Map()
socket.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg)
    pending.delete(msg.id)
  }
}
function send(method, params = {}) {
  return new Promise((resolve) => {
    const mid = ++id
    pending.set(mid, resolve)
    socket.send(JSON.stringify({ id: mid, method, params }))
  })
}
socket.onopen = async () => {
  await send('Runtime.enable')
  await send('Runtime.evaluate', {
    awaitPromise: true,
    expression: `(() => {
      const model = globalThis.monaco?.editor?.getModels?.()[0]
      if (!model) throw new Error('Monaco model not found')
      model.setValue(${JSON.stringify(manifest)})
      const markers = globalThis.monaco.editor.getModelMarkers({ resource: model.uri })
      return JSON.stringify({ equal: model.getValue() === ${JSON.stringify(manifest)}, markers })
    })()`,
    returnByValue: true,
  }).then((res) => console.log(res.result.result.value))
  socket.close()
}
NODE
```

## Network And Evidence

Capture broad browser-visible traffic, but remember HTTP plugin execution can be
server-side and may not appear as a browser request to `cnxpluginsweb`.

Track:

- `copilotweb`
- `directline`
- `cnxpluginsweb`
- `/plugins/`
- `/preview-plugins/`
- `conversation`
- `activities`
- `orchestr`
- `plugin`

Useful evidence for success:

- Scoped conversation start posts `mode: "agent"` and
  `competency.id: "BicepDeploymentDebug"`.
- Copilot sidecar shows the exact working prompt.
- Activity names `Deploy built-in Bicep debug sample and request confirmation`.
- Confirmation card renders before side effects.
- Approved retry shows compile, ARM submit, accepted, and terminal success.
- For smoke validation, it is useful evidence if the sidecar shows the exact
  prompt, `Agent has been registered`, `Plugin has been registered`, and a Bicep
  deployment activity/tool handoff. Deployment can still fail later because of
  RBAC, quota, ARM validation, or a corrupted pasted manifest.

Do not print raw `copilotweb /api/conversations/start` or DirectLine response
bodies. They can contain DirectLine bearer tokens. Summaries should include
status code, URL, sanitized conversation IDs, mode, competency, activity names,
correlation IDs, `Location`, and `Retry-After` when available.

## Bicep Plugin Contract

- Deploy endpoint:
  `POST https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/deploy`.
- Status endpoint:
  `GET https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/subscriptions/{subscription_id}/deployments/{deployment_name}`.
- Auth type: `EntraOnBehalfOf`.
- Auth scope: `1dce83cb-ee48-4e43-bd08-a23fd936428e/.default`.
- Required request fields: `bicep_config`, `subscription_id`, `location`,
  `async_response`, and `messageLocale`.
- `bicep_config.parts[0].data.files` must contain `file_name` and `content`.
- Without `confirmation`, the endpoint returns the HTTP confirmation envelope
  and must not perform side effects.
- With `confirmation: true`, the endpoint starts deployment and returns `202`
  with `Location` and `Retry-After`.
- Current source default for Bicep polling is `Retry-After: 10`.

## Failure Guide

- `Sorry, I can't help with that`: avoid pasted Bicep source, fenced code, raw
  JSON, fake subscriptions, or the wrong competency. Use the built-in sample
  manifest and working prompt.
- Query/storage agent runs: you used lower `CopilotTopActions` or left the
  default `ArgStorage` form in play. Close Copilot and use only the upper API
  scoped form.
- Disabled `Register`: read Monaco markers. If markers are empty but the button
  was already disabled before the click, reload Portal and use a fresh target.
- Sidecar shows old prompt: stale Copilot iframe or wrong SideLoad target. Close
  Copilot, reload if needed, and submit from the registered SideLoad iframe.
- No browser `cnxpluginsweb` request: not necessarily failure. Correlate with
  Copilot activity, DevUI/service logs, and final UI output.
- `/auth/login/`: wait briefly and retry the Portal URL in the same page/profile
  once. Only ask the user to sign in if the retry still lands on login.
- Bicep agent is hit but tool execution fails or falls back to conversational
  confirmation: verify the registered Monaco content exactly matches the
  manifest file. If Lua quotes are missing, the manifest was corrupted during
  paste; reload SideLoad and paste via direct CDP/file or a quoted heredoc.
- `ECONNREFUSED 127.0.0.1:9222`: Playwriter used the Windows-local WebSocket
  URL. Use `ws://<wsl-gateway>:9223/...`.
- Playwriter command times out while Portal is still working: rerun the command
  with the Playwriter CLI timeout flag, for example `--timeout 120000`. This is
  separate from Playwright action or navigation timeouts inside the script.

## Cleanup

Close the temporary debug Edge window when finished. If desired, remove the WSL
proxy and firewall rule from elevated Windows PowerShell:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=9223
Remove-NetFirewallRule -DisplayName "Edge CDP from WSL"
```
