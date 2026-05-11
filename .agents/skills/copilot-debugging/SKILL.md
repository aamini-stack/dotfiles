---
name: copilot-debugging
description: Debug Azure Copilot HTTP plugins against a real Copilot or Azure Portal client using the user's Chrome session, Playwriter, network traces, AXEAgents auth contracts, and service logs. Use when testing Copilot plugin behavior, confirmation flows, polling/LROs, token acquisition, or client/service mismatches.
---

# Copilot Plugin Debugging

Use this skill to debug Azure Copilot HTTP plugins end-to-end with a real browser and client. Prefer the real client over synthetic curl tests when the issue involves auth, Copilot confirmation, polling, adaptive UI rendering, plugin routing, or headers.

## Required Tools

- Load and follow the `playwriter` skill before browser automation.
- Use the user's existing Chrome session through Playwriter extension mode unless the user explicitly asks for direct CDP.
- If Playwriter reports no connected browser, ask the user to click the Playwriter extension icon on the target Copilot or Azure Portal tab.
- If the target UI is Azure Portal Copilot in Edge, expect the chat surface to be hosted in a cross-origin sandbox iframe such as `CopilotFluentAI.ReactView`. Extension mode can capture top-level Portal traffic but may not enter that iframe. Use direct CDP for full automation.
- Direct CDP requires the browser to expose a DevTools endpoint. Opening `edge://inspect` is usually not enough; Edge often must be launched with `--remote-debugging-port=9222`.

## AXEAgents Contract

For this repo, the Copilot-facing service is AXEAgents/CnxPlugins.

- First-party app/resource ID: `1dce83cb-ee48-4e43-bd08-a23fd936428e`.
- Portal token acquisition must use `Az.getAuthorizationToken({ resourceName: "cnxplugins" })`.
- API requests must pass `Authorization: authToken.header`, not the raw token object.
- Stable routes are under `/plugins`.
- Preview routes are under `/preview-plugins`.
- Regional hosts include `https://cnxpluginsweb.canary.production.portalrp.azure.com` and `https://cnxpluginsweb.production.portalrp.azure.com`.
- Key request headers for correlation include `x-ms-correlation-id`, `x-ms-conversation-id`, `x-ms-client-request-id`, `x-ms-client-session-id`, `x-ms-plugin`, `x-ms-mode`, and `x-ms-agent`.

## Copilot Debug URLs And Flags

Use the local cloned PortalFx docs before relying on memory. Relevant docs are under `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/`.

Key files:

- `plugin-e2e-setup.md` — end-to-end Copilot/plugin debug URL and sideload setup.
- `agents-sideloading.md` — debug mode behavior and what to inspect.
- `scoped-conversations-copilot.md` — competency filter rules for scoped agent conversations.
- `direct-agent-invocation.md` — constraints for direct agent execution experiments.
- `http-confirmation.md` — HTTP confirmation response and retry schema.
- `develop-httpplugin.md` — HTTP plugin headers, auth, data boundary, supported interactions.

Doc-backed debug flags for Copilot plugin E2E testing:

```text
https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&exp.pluginstoredeclarativehttpplugins=true&exp.AzCopilot_ArgQueryGenerator_plugin=15.0&exp.AzCopilot_ArgQueryRunner_plugin=15.0&exp.azurepluginstore=true&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&Microsoft_Azure_Copilot_clientoptimizations=false&feature.customportal=false&feature.canmodifyextensions=true#home
```

In practice, use this fuller debug URL when validating sideloaded agents/plugins and DevUI visibility:

```text
https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.AzCopilot_ArgQueryGenerator_plugin=15.0&exp.AzCopilot_ArgQueryRunner_plugin=15.0&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&Microsoft_Azure_Copilot_clientoptimizations=false&feature.customportal=false&feature.canmodifyextensions=true#home
```

When sideloading a local CopilotExtension, append the documented test extension hash:

```text
#home?testExtensions=%7B%22Microsoft_Azure_Copilot%22:%22https://localhost:1339/copilotextension%22%7D
```

For the AXEAgents health/debug client in this workspace, use the documented ContainerService flight URL:

```text
https://ms.portal.azure.com/?feature.canmodifystamps=true&Microsoft_Azure_ContainerService=flight13#view/Microsoft_Azure_ContainerService/CnxPluginsClient.ReactView
```

`feature.unifiedcopilotdebug=true` makes Copilot show detailed debug information, including selected agent/plugin, execution details, handler responses, arguments/parameters, and technical identifiers. Use it when validating that the orchestrator selected and invoked the expected plugin.

Additional doc-backed flags can be necessary depending on which Copilot debug surface is being tested:

- `feature.azurepluginstore=true` — documented sideload flag for plugin/agent registration in the Copilot sidecar.
- `feature.inlinecopilot=true` — documented for the Inline Copilot testing blade.
- `feature.devui=true` and `feature.canarytraffic=true` — documented for DevUI scenarios.
- `exp.useRegionalEndpoint=true` — documented RC validation flag for plugin store scenarios.

If the “Test your plugin or agent” status bar is visible but clicking it does nothing, verify both `feature.azurepluginstore=true` and `feature.unifiedcopilotdebug=true` are present. In this session, adding Agent mode and the broader debug flags made the sidecar visible and Agent mode toggle work, but did not fix the inert registration banner; the next fallback is to locate the underlying registration API/client state or test through chat with network capture enabled.

For agent/plugin execution testing, enable Agent mode in the Copilot sidecar before submitting the prompt. In the current Copilot UI the button is at the bottom composer bar, has `aria-label="Agent"`, `data-testid="copilot-toggle-agentmode"`, and changes from `aria-pressed="false"` to `aria-pressed="true"` when enabled. Agent mode is required for agent-backed sideloaded plugin testing, but enabling it does not by itself open the sideload registration UI.

Observed sequence for DevUI/debug visibility:

1. Navigate to the full RC debug URL above.
2. Open the Copilot sidecar from the top-bar Copilot button.
3. Enable Agent mode from the bottom composer bar.
4. Confirm `aria-pressed="true"` on the `data-testid="copilot-toggle-agentmode"` button.
5. The DevUI link/debug affordance may appear only after Agent mode is enabled.

## SideLoad Blade Workflow

Use the SideLoad blade rather than only the Copilot banner when validating sideloaded agents/plugins. The banner can be inert even when the blade and APIs work.

Open the SideLoad blade from Portal with:

```js
az.openBlade({ extensionName: "Microsoft_Azure_Copilot", bladeName: "SideLoad.ReactView" })
```

Expected Portal hash:

```text
#view/Microsoft_Azure_Copilot/SideLoad.ReactView
```

Observed iframe roles in RC Portal direct CDP sessions:

- `sandbox-1.reactblade-rc.portal.azure.net` commonly hosts `CopilotFluentAI.ReactView`.
- `sandbox-2.reactblade-rc.portal.azure.net` commonly hosts `SideLoad.ReactView`.
- The target IDs change per session, so always inspect `/json/list` and match by page text/title, not by a stored target ID.

SideLoad registration checks:

- Paste complete JSON with both `AiPlugins` and `AiAgents`; do not paste only the plugin manifest.
- Read Monaco markers after paste. A disabled Register button with Monaco markers means schema validation failed.
- After a successful Register click, the Register/Test Plugins buttons may become disabled. Treat that as a likely post-submit state, but verify by running a scoped conversation and watching network/DevUI.
- The editor may show “Made N formatting edits...” after accepted formatting; this is not a failure.
- Do not assume model names from docs. Use the exact model enum accepted by the current SideLoad validator.

## Scoped Conversations To Force Tool Selection

Use scoped conversations when normal Agent mode chooses the wrong agent/plugin. This is the preferred way to validate a specific sideloaded deployment plugin because it filters Plugin Store tools before orchestration.

Docs: `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/scoped-conversations-copilot.md` and `direct-agent-invocation.md`.

Rules:

- Scoped conversations are available only in Advanced/Agent mode.
- The competency filter is `<Client>Advanced:<CompetencyId>`.
- For RC Portal, use `AzurePortalRCAdvanced:<CompetencyId>`.
- Add that exact string to `allowedClients` on every sideloaded agent/plugin that should participate.
- Tools without the exact scoped client string are excluded from that scoped conversation.
- The SideLoad blade includes a `Scoped Conversations` tab for testing with a prompt and competency.
- The scoped nudge should start a new `mode: "agent"` conversation through `https://copilotweb.canary.production.portalrp.azure.com/api/conversations/start?api-version=2025-08-15` with body like `{"conversationType":"Chat","mode":"agent","competency":{"id":"<CompetencyId>","displayName":""}}`.
- A successful scoped conversation start only proves the nudge/scope was accepted. It does not prove the HTTP plugin ran; confirm with DevUI and AXEAgents service/network traces.

Example scoped client string for a deployment-only Bicep test:

```text
AzurePortalRCAdvanced:BicepDeploymentDebug
```

For direct agent execution experiments, the scoped conversation must return exactly one agent and zero plugins, and the agent reasoning description must be empty. For normal agent-plus-plugin testing, include both the agent and the plugin under the same competency-scoped `allowedClients` value so orchestration can select the intended deployment plugin without unrelated tools.

For agent-plus-plugin SideLoad testing:

- The plugin `allowedClients` should include `Agent:<AgentName>` so the agent can use that plugin.
- The plugin should also include the exact scoped client string, for example `AzurePortalRCAdvanced:BicepDeploymentDebug`, when it should be visible in scoped advanced mode.
- The agent `allowedClients` should include the exact scoped client string.
- Set `isLKG: true` for sideloaded scoped testing unless intentionally validating flight/experiment behavior.
- Keep function names unique and aligned between `functions[*].name` and `runtimes[*].run_for_functions`.
- Keep the agent `runtimes[*].run_for_functions` aligned to the agent function name.

Prompting tips for side-effecting deployment plugins:

- Make the prompt deployment-only: provide already-valid files and tell Copilot not to generate or rewrite infrastructure code.
- Ask for the plugin confirmation flow first if the endpoint requires confirmation.
- If Copilot responds with only reasoning and `0 actions completed`, the turn may not have selected/executed the plugin yet even though the scoped conversation started correctly.
- If the user can see the plugin was called in DevUI/service logs, trust the real client evidence over a too-narrow browser network filter.

Sideload schema validator note: the model enum can differ from public model names and older docs. In this session, `gpt-4o` and `gpt4o` were rejected and the editor marker said the valid value was `gpt-5-mini`. Always read Monaco markers after pasting schema and use the exact model value accepted by the current sidecar validator.

Raw CDP check/toggle pattern for the Copilot iframe target:

```js
(() => {
  const button = Array.from(document.querySelectorAll("button"))
    .find((el) => el.getAttribute("aria-label") === "Agent");
  if (!button) return { found: false };
  if (button.getAttribute("aria-pressed") !== "true") button.click();
  return {
    found: true,
    enabled: button.getAttribute("aria-pressed") === "true",
    testId: button.getAttribute("data-testid"),
  };
})()
```

## Debugging Workflow

1. Identify the route and client surface.
2. Read the local endpoint handler, request/response model, tests, and relevant docs before opening the browser.
3. Build an expected contract checklist: method, URL, request body shape, auth audience/resource, response shape, status code, headers, and polling behavior.
4. Start a Playwriter session and attach to the real Copilot/Portal tab.
5. Observe the page first: print URL and run `snapshot({ page })`.
6. Add browser-side network capture for the target host or route before reproducing. For Portal Copilot, capture all relevant page, iframe, and worker targets, not only the visible iframe.
7. Reproduce with one user-visible action at a time.
8. After each action, observe URL, snapshot, console errors, and captured requests/responses.
9. Correlate browser request IDs with service logs using `x-ms-correlation-id`, `x-ms-conversation-id`, and deployment/job IDs in response bodies or `Location` headers.
10. Fix the smallest correct issue in code or configuration, then verify with unit tests and the real client.

## Edge And WSL Direct CDP Setup

When the agent shell runs in WSL/Linux and the user browser is Microsoft Edge on Windows, extension mode may connect but direct CDP auto-discovery may fail. For Azure Portal Copilot, direct CDP is required for reliable automation because the chat surface runs in a cross-origin sandbox iframe.

Use this setup when the normal `playwriter session new --direct` command cannot discover Edge.

### 1. Launch Edge With A Debug Port

Run one of these from Windows PowerShell. `msedge.exe` may not be on `PATH`, so prefer the full path.

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"
```

Fallback path:

```powershell
& "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"
```

Open Azure Portal/Copilot in that Edge window and sign in.

### 2. Verify Edge From Windows

Run this from Windows PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

Expected result includes a `webSocketDebuggerUrl`, usually like:

```text
ws://127.0.0.1:9222/devtools/browser/<browser-id>
```

### 3. Expose The Debug Port To WSL

If WSL cannot reach `127.0.0.1:9222` or the Windows host gateway, add a Windows port proxy. Run Windows PowerShell as Administrator:

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9223 connectaddress=127.0.0.1 connectport=9222
New-NetFirewallRule -DisplayName "Edge CDP from WSL" -Direction Inbound -LocalPort 9223 -Protocol TCP -Action Allow
```

From WSL, the Windows host gateway is usually the nameserver/default gateway:

```bash
ip route
cat /etc/resolv.conf
```

Verify the proxied endpoint from WSL:

```bash
curl http://$(ip route | awk '/default/ {print $3}'):9223/json/version
curl http://$(ip route | awk '/default/ {print $3}'):9223/json/list
```

The returned `webSocketDebuggerUrl` should contain the WSL-reachable host and port, for example:

```text
ws://172.28.240.1:9223/devtools/browser/<browser-id>
```

### 4. Start Playwriter Direct Mode

Use the exact `webSocketDebuggerUrl` returned by the WSL `curl` command:

```bash
playwriter session new --direct ws://172.28.240.1:9223/devtools/browser/<browser-id>
```

Then list pages:

```bash
playwriter -s <session> -e 'console.log(JSON.stringify(browser.contexts().map((c, ci) => ({ context: ci, pages: c.pages().map((p, pi) => ({ page: pi, url: p.url() })) })), null, 2))'
```

### Troubleshooting

- If `msedge.exe` is not recognized, use the full path shown above.
- If Windows `Invoke-RestMethod http://127.0.0.1:9222/json/version` fails, Edge was not launched with remote debugging or another Edge process reused the profile. Close the debug Edge window and relaunch with a temporary `--user-data-dir`.
- If Windows can reach `127.0.0.1:9222` but WSL times out, use the `netsh interface portproxy` and firewall rule on port `9223`.
- If Playwriter direct connects but later reports `ECONNREFUSED 127.0.0.1:9222`, do not use the Windows-local WebSocket URL. Use the WSL-reachable WebSocket URL returned by `curl http://<gateway>:9223/json/version`.
- `playwriter browser list` is useful for extension-connected browsers, but direct CDP in WSL/Windows scenarios is usually more reliable with an explicit `ws://.../devtools/browser/...` endpoint.

Security note: a remote debugging port can expose browser control. Use a temporary Edge profile, bind only as broadly as necessary, keep it on trusted networks, and close the debug Edge window when finished. Remove the proxy/rule when no longer needed if desired.

## Playwriter Network Capture Pattern

Install listeners before triggering the Copilot action:

```js
state.requests = [];
state.responses = [];
state.page.on("request", (req) => {
  const url = req.url();
  if (url.includes("cnxpluginsweb") || url.includes("/plugins/") || url.includes("/preview-plugins/")) {
    state.requests.push({
      url,
      method: req.method(),
      headers: req.headers(),
      postData: req.postData(),
    });
  }
});
state.page.on("response", async (res) => {
  const url = res.url();
  if (url.includes("cnxpluginsweb") || url.includes("/plugins/") || url.includes("/preview-plugins/")) {
    let body = "";
    try { body = await res.text(); } catch {}
    state.responses.push({
      url,
      status: res.status(),
      headers: res.headers(),
      body: body.slice(0, 8000),
    });
  }
});
```

Summarize after reproduction:

```js
console.log(JSON.stringify({
  requests: state.requests.map((r) => ({
    method: r.method,
    url: r.url,
    correlationId: r.headers["x-ms-correlation-id"],
    conversationId: r.headers["x-ms-conversation-id"],
    plugin: r.headers["x-ms-plugin"],
    mode: r.headers["x-ms-mode"],
    agent: r.headers["x-ms-agent"],
    hasAuthorization: Boolean(r.headers.authorization),
    postData: r.postData,
  })),
  responses: state.responses.map((r) => ({
    status: r.status,
    url: r.url,
    location: r.headers.location,
    retryAfter: r.headers["retry-after"],
    body: r.body,
  })),
}, null, 2));
```

Always clean up listeners when finished:

```js
state.page.removeAllListeners("request");
state.page.removeAllListeners("response");
```

## Direct CDP Network Capture Pattern

For Azure Portal Copilot, important requests often originate from workers under the top-level Portal origin rather than the visible Copilot iframe. A narrow filter on only `cnxpluginsweb` or only the current iframe can miss the successful path.

Checklist:

- Enable `Network.enable` on the top-level Portal page, the Copilot iframe, the SideLoad iframe, and Portal blob workers returned by `http://<gateway>:9223/json/list`.
- Filter after capture for `copilotweb`, `directline`, `cnxpluginsweb`, `/plugins/`, `/preview-plugins/`, `conversation`, `chat`, `orchestr`, and `plugin`.
- Include request bodies for `copilotweb.../api/conversations/start` and `directline.../activities`; these show whether scoped nudge and user turn payloads were sent.
- Include `x-ms-client-request-id`, `x-ms-correlation-request-id`, `x-ms-request-id`, `mise-correlation-id`, DirectLine conversation ID, and any plugin-specific correlation headers.
- Do not print full bearer tokens in summaries or skill notes. Redact `Authorization` values.

Important browser-visible calls:

- Scoped conversation start: `POST https://copilotweb.canary.production.portalrp.azure.com/api/conversations/start?api-version=2025-08-15`.
- Chat history/status polling: `GET https://copilotweb.canary.production.portalrp.azure.com/api/chats?api-version=2025-08-15`.
- User turn delivery: `POST https://directline.botframework.com/v3/directline/conversations/<id>/activities`.
- Plugin execution may not appear as a browser `cnxpluginsweb` request because HTTP plugins are called server-side by orchestrator. Validate with Copilot DevUI and AXEAgents/service logs when browser traffic only shows DirectLine/CopilotWeb.

## Copilot HTTP Confirmation Checks

When debugging confirmation flows, verify both the pre-confirmation and post-confirmation calls.

- The first call must not perform side effects.
- The response must use the exact envelope expected by the orchestrator.
- In this repo's Bicep preview plugin, the envelope is `{"Data":{"Type":"Confirmation","Message":"..."}}`; casing is intentional.
- The confirmed retry may send `confirmation: true` or the string form `"true"`; tests should cover both if the spec uses a string example.
- Validate user-input errors before returning a confirmation prompt when the request would fail anyway.

## Polling And LRO Checks

For async operations, verify the full polling chain.

- Initial accepted response should be `202` with `Location` and `Retry-After`.
- `Location` should be absolute if the real Copilot client requires absolute URLs.
- `Location` must point to the same environment as the initial request unless cross-environment routing is intentionally tested.
- Poll responses should return `202` with `Location` and `Retry-After` while non-terminal.
- Terminal response should include the Copilot UI payload expected by the client.
- Preserve a stable deployment/job ID across initial response, polls, service logs, and downstream ARM calls.

## Common Failure Modes

- `401`: extension not pre-authorized, wrong `resourceName`, wrong token audience, or `Authorization` header omitted.
- `403`: token valid but principal lacks ARM/resource permission.
- Browser CORS/trusted-domain failure: extension config is missing the target host under trusted domains.
- Confirmation card missing: response envelope casing or structure does not match the Copilot spec.
- Polling stops early: non-terminal state returned without `202`, `Location`, or `Retry-After`.
- Polling hits the wrong environment: `Location` host differs from the host being tested.
- UI shows generic failure: service returned a body shape Copilot cannot render or omitted the expected `data.status`/artifacts shape.
- Synthetic tests pass but real client fails: missing real headers, token audience mismatch, or client-specific confirmation/polling behavior.
- Scoped conversation starts but plugin does not run: competency accepted, but tool was not selected, agent/plugin was absent from orchestration, agent did not call the function, or prompt was refused by safety/policy before execution.
- Browser trace lacks `cnxpluginsweb`: not necessarily failure. HTTP plugin calls can be server-side from orchestrator; use DevUI and service logs for final confirmation.
- SideLoad prompts file 404 such as `generated/Loc/en/agents/<Competency>_prompts.json`: observed during scoped SideLoad testing and not by itself a blocker.

## AXEAgents Bicep Route Notes

The Bicep preview route is a useful reference implementation for this workspace.

- Deploy endpoint: `POST /preview-plugins/bicep/deploy`.
- Status endpoint: `GET /preview-plugins/bicep/subscriptions/{subscription_id}/deployments/{deployment_name}` when mounted through the preview router.
- The handler validates filenames before confirmation.
- Without confirmation it returns a Copilot confirmation envelope and skips blob, compile, and ARM side effects.
- With confirmation it uploads if blob storage is configured, compiles Bicep, creates an ARM deployment, and returns `202` with polling headers.
- Current code pins polling `Location` to canary for real-client testing; remove or make environment-driven before production rollout.

Useful Bicep SideLoad manifest shape for deployment-only testing:

- Plugin endpoint: `https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/deploy`.
- Auth type: `EntraOnBehalfOf`.
- Auth scope: `1dce83cb-ee48-4e43-bd08-a23fd936428e/.default`.
- Function parameters should include `bicep_config`, `subscription_id`, `location`, `async_response`, and `messageLocale`.
- Lua payload script can convert a prompt-provided `bicep_files` array into `bicep_config.parts[0].data.files` before calling the endpoint.
- The initial expected endpoint response is the confirmation envelope unless `confirmation` is already true.

## Minimum Verification

- Run focused unit tests for the plugin route and model behavior.
- Reproduce once through the real Copilot/Portal client with Playwriter network capture enabled.
- Capture status code, `Location`, `Retry-After`, correlation ID, conversation ID, and the rendered Copilot UI result.
- If logs are available, verify the same correlation/deployment IDs appear in service traces.
