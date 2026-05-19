---
name: copilot-debugging
description: Debug the Bicep HTTP plugin in real Azure Portal Copilot with SideLoad and Playwriter direct CDP.
---

# Bicep Copilot Debug

Use real Portal Copilot for routing, confirmation cards, auth, and LRO polling.

Do first:

```bash
playwriter skill
```

For local endpoint testing, run the cloudflared skill first and use the tunnel URL
in the registered manifest.

Use Playwriter direct CDP. Do not use Playwriter extension mode for this flow:
Portal hosts SideLoad/Copilot in sandboxed cross-origin React blade OOPIFs, and
extension mode currently misroutes or loses those iframe sessions.

This task is the explicit direct-CDP exception to Playwriter's usual extension
mode preference. The Portal iframe/OOPIF behavior has been unreliable through
extension mode, while direct CDP can consistently inspect and interact with the
SideLoad and Copilot frames.

If a WSL portproxy was already set up by a previous session, try it before asking
the user to relaunch Edge:

```bash
GW=$(ip route | awk '/default/ {print $3; exit}')
curl -sS "http://${GW}:9223/json/version"
WS_URL=$(node -e 'fetch(process.argv[1]).then(r => r.json()).then(j => console.log(j.webSocketDebuggerUrl))' "http://${GW}:9223/json/version")
playwriter session new --direct "${WS_URL}"
```

Launch Edge CDP from Windows PowerShell. Admin is not required for Edge:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"
```

If the agent runs from WSL, paste this in elevated Windows PowerShell:

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9223 connectaddress=127.0.0.1 connectport=9222
New-NetFirewallRule -DisplayName "Edge CDP from WSL" -Direction Inbound -LocalPort 9223 -Protocol TCP -Action Allow
```

Connect from WSL:

```bash
curl -sS "http://$(ip route | awk '/default/ {print $3}'):9223/json/version"
playwriter session new --direct ws://<wsl-gateway>:9223/devtools/browser/<browser-id>
```

Portal URL:

```text
https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&feature.customportal=false&feature.canmodifyextensions=true#view/Microsoft_Azure_Copilot/SideLoad.ReactView
```

Register manifest:

```text
.agents/skills/copilot-debugging/bicep-deployment-debug.manifest.json
```

Automated invalid-Bicep repro:

```bash
playwriter -s <session-id> --timeout 180000 -e "globalThis.AZURE_SUBSCRIPTION_ID='<subscription-id>'; $(cat .agents/skills/copilot-debugging/repro-invalid-bicep.playwriter.js)"
```

Automated plain-English valid deploy repro against a local tunnel:

```bash
playwriter -s <session-id> --timeout 240000 -e "globalThis.AZURE_SUBSCRIPTION_ID='<subscription-id>'; globalThis.BICEP_DEBUG_MODE='valid'; globalThis.BICEP_DEPLOY_URL='<tunnel-url>/preview-plugins/bicep/deploy'; $(< .agents/skills/copilot-debugging/repro-plain-english-bicep.playwriter.js)"
```

Do not wrap these repro scripts in `eval(require('node:fs').readFileSync(...))`.
They use top-level `await`; `eval(...)` runs them in a non-module/function context
and fails with `SyntaxError: await is only valid in async functions and the top
level bodies of modules`. Inject the script text directly with shell substitution
as shown above.

Always pass an explicit Playwriter timeout. Portal load, SideLoad registration,
agent routing, confirmation, and LRO polling regularly exceed Playwriter's
default 10 second eval timeout.

The script generates a unique deployment label by default. Reusing the same prompt/label in one sidecar can lead to stale Copilot conversation behavior.

For local tunnel tests, replace the manifest runtime URL with:

```text
$TUNNEL_URL/preview-plugins/bicep/deploy
```

Before approving any confirmation card, verify the local API and tunnel are both
healthy. If the API was edited after it started, restart it first; a stale reload
child can keep serving old code even when the file on disk is fixed.

```bash
curl -fsS http://127.0.0.1:2750/healthcheck
curl -fsS "$TUNNEL_URL/healthcheck"
```

Find the real live API log from the process stdout/stderr, not from memory:

```bash
ss -ltnp 'sport = :2750'
readlink -f /proc/<api-pid>/fd/1 /proc/<api-pid>/fd/2
```

In this repo the active dev log has been `/tmp/opencode/workloads-bicep-api.log`.
Older files such as `/tmp/opencode/wac-api.log` may only contain a failed restart
like `Address already in use` and are not evidence about the live server. The log
may contain binary/control bytes; search it with `rg -a`.

SideLoad flow:

```text
If testing local code, start API + cloudflared and patch manifest URL.
Register tab -> paste manifest -> Register
Scoped Conversations tab -> upper API form only
Competency: BicepDeploymentDebug
Prompt: Deploy the built-in Bicep debug sample to subscription <subscription-id> in eastus. Use deployment label copilot-bicep-debug. Show the deployment confirmation first.
Submit -> approve confirmation -> wait for LRO output
```

Repro workflow details learned the hard way:

```text
Use clipboard paste, not keyboard insertText, for full manifests. insertText is slow and can leave Monaco with partial content if the default 10s Playwriter eval timeout fires.

Browser clipboard writes require the Portal tab/document to be focused. Call `page.bringToFront()` and click Monaco before `navigator.clipboard.writeText(...)`.

After paste, verify Monaco's model contains expected manifest markers before clicking Register. Clipboard paste can silently fail or leave stale content in the editor.

Saved Playwriter sessions can have a non-Portal tab as `state.page`; choose an existing `https://rc.portal.azure.com/` page from `context.pages()` or create a new page before opening SideLoad.

SideLoad remembers the last selected tab. Use role-based tab locators like `getByRole("tab", { name: "Plugin & Agent Test" })` / `getByRole("tab", { name: "Scoped Conversations" })`; text-filtered `button` locators can time out against these Fluent UI tabs.

Copilot confirmation wording can vary. The direct plugin card may say `Type "confirm" to proceed` with a `confirm` button, while agent-mediated flows may show `Planned deployment details` or `Deployment confirmation` with `yes` / `no` or `Confirm` / `Cancel` buttons. Automation should accept all observed forms and click the affirmative button.

The invalid-Bicep repro should log each milestone: Portal opened, SideLoad frame found, manifest pasted and verified, Register clicked, Scoped Conversations submitted, confirmation frame found, confirmation clicked, and final Copilot output captured.

If the sidecar returns `Sorry, I wasn't able to respond to that` with ActivityId/Correlation ID before confirmation, treat it as a transient Copilot/service failure. Rerun with a fresh SideLoad/sidecar and unique deployment label before debugging the plugin itself.
Do not judge manifest validity from Monaco word-wrap indentation. Long JSON string values wrap visually and look misindented even when valid.
If quotes inside the Lua script are built from a shell-quoted -e string, verify the resulting script text. Shell quoting can silently strip Lua single quotes and produce invalid payload code.
After a partial or bad paste, reload the SideLoad blade before trying again. A fresh blade plus clipboard paste let Register become enabled.
Prefer frame-scoped locators over screenshot coordinates. The SideLoad form is in sandbox-1.reactblade and Copilot is usually in another sandbox frame.
If coordinates are unavoidable, remember screenshots are device pixels while Playwright mouse coordinates are CSS pixels. In the captured session deviceScaleFactor was 1.5, so coordinate clicks missed buttons until scaled.
The upper Scoped Conversations API form is the one to use. The lower CopilotTopActions form still defaults to ArgStorage and can create misleading storage runs.
Set the upper competency input explicitly and verify it changed from ArgStorage to BicepDeploymentDebug before Submit.
Registration can look quiet. In this session the strongest evidence was Register becoming disabled, then the Scoped Conversations flow showing Agent has been registered and Plugin has been registered inside Copilot.
The Copilot sidecar content is not visible in the main document body. Find the frame whose body contains the live Copilot text, then click confirm inside that frame.

Fresh local routing is proven by live API log rows for POST /preview-plugins/bicep/deploy and GET /preview-plugins/bicep/subscriptions/.../deployments/..., not by Copilot prose alone. If cloudflared has no incoming requests and the API log has no deployment label, assume stale SideLoad/canary routing.

After a code fix, restart the local API before approving a pending card. In one run, the file on disk defined _FAILED_RESOURCES_LOG_CAP but the live process did not; the status GET crashed with NameError until the dev API was restarted.

If the confirmation card is visible but button locators cannot see it, screenshot coordinates are a last resort. Playwright mouse coordinates are CSS pixels; screenshot images shown in chat may be device pixels or resized. Measure window.devicePixelRatio and viewport size, then use a screenshot captured with scale: "css" to calculate coordinates.

Do not treat `Reasoning complete` or `Deployment accepted by ARM` as success. Success requires a terminal status GET/log row (`deployment_state_terminal ... state: Succeeded`) or final Copilot text naming the deployment/resource as Succeeded.

Copilot's activity header can show `0 artifacts created` even when the final answer says `Artifact produced: Deployment Results (...)`. Treat this as an artifact rendering/count bug to investigate separately from deployment success.
```

Expected confirmation:

```text
Are you sure you want to deploy this Bicep configuration?
Subscription: <subscription-id>
Location: eastus
Files: 2 file(s) - main.bicep, vm.bicep
```

Expected VM sample terminal output:

```text
Compiling bicep templates...
Submitting deployment to ARM...
Deployment accepted by ARM.
vm-debug-nested - Failed
rg-copilot-bicep-debug - Succeeded
Deployment failed!
```

Rules:

```text
Use Playwriter direct CDP, not extension mode.
Use the upper SideLoad API form, not CopilotTopActions.
Register and submit from the same SideLoad iframe.
Select Copilot iframe by live text, not newest target ID.
Do not print bearer tokens, DirectLine tokens, or auth attachment bodies.
Do not paste Bicep source into the prompt.
If SideLoad is stale, reload Portal and use a fresh iframe.
Current Retry-After is 10.
```

Failure hints:

```text
Sorry, I can't help with that -> wrong competency, stale iframe, bad manifest, or source pasted into prompt.
ArgStorage/storage query runs -> lower form was used or React state was not updated.
No browser cnxpluginsweb request -> plugin execution can be server-side; inspect Copilot activity and service logs.
No local tunnel/API request for the fresh label -> stale SideLoad registration, stale Monaco model, or the manifest still contains the canary URL. Re-register with unique plugin/agent/function names and verify Monaco contains only the tunnel URL.
Disabled Register -> inspect Monaco markers; if empty, reload and use a fresh SideLoad blade.
Register enabled but click does nothing -> you are probably clicking the iframe boundary or using unscaled screenshot coordinates; use the sandbox frame locator.
Prompt runs but asks about storage -> upper competency stayed ArgStorage or lower form was used.
Client shows { m_MaxCapacity, Capacity, m_StringValue: "Error executing function", m_currentThread } -> invalid-Bicep repro succeeded and the client hid the real compilation details behind the generic function error.
Status GET returns 500 after ARM PUT succeeded -> inspect the live API log with `rg -a` for Python exceptions, then restart the dev API if the process is stale.
```

Cleanup:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=9223
Remove-NetFirewallRule -DisplayName "Edge CDP from WSL"
```
