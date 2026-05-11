---
name: copilot-debugging
description:
  Debug Azure Copilot HTTP plugins end-to-end in a real Azure Portal/Copilot
  browser session using Playwriter direct CDP, network traces, AXEAgents auth
  contracts, and service logs.
---

# Copilot Plugin Debugging

Use this skill to validate Azure Copilot HTTP plugins against the real Azure
Portal/Copilot client. Prefer this over curl or synthetic tests when debugging
auth, plugin routing, confirmation cards, LRO polling, scoped conversations,
DevUI, or client/service mismatches.

## Hard Rules

- Always load and follow the `playwriter` skill first.
- Always run `playwriter skill` before browser automation.
- Always use Playwriter direct CDP for Azure Portal Copilot. Do not use
  extension mode for Portal Copilot because the chat and sideload surfaces run
  in cross-origin sandbox frames/workers.
- Always print the CDP setup commands for the user before trying to connect.
- Always use a temporary debug browser profile.
- Never print bearer tokens. Redact `Authorization` values in summaries.
- Verify the real client end-to-end; browser traces alone may not show HTTP
  plugin execution because the orchestrator can call plugins server-side.

## CDP Setup To Print First

Print this block to the user before starting a Portal Copilot debugging session.

```powershell
# 1. Launch Edge with CDP from Windows PowerShell.
# Close any previous debug Edge window first.
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"

# Fallback path if needed:
& "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"

# 2. Verify Edge is actually listening on Windows.
Invoke-RestMethod http://127.0.0.1:9222/json/version

# 3. If the agent runs in WSL/Linux, expose CDP to WSL.
# Run PowerShell as Administrator.
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9223 connectaddress=127.0.0.1 connectport=9222
New-NetFirewallRule -DisplayName "Edge CDP from WSL" -Direction Inbound -LocalPort 9223 -Protocol TCP -Action Allow

# 4. Confirm the proxy exists if troubleshooting.
netsh interface portproxy show v4tov4
```

Then verify from WSL/Linux:

```bash
curl -sS --max-time 5 "http://$(ip route | awk '/default/ {print $3}'):9223/json/version"
curl -sS --max-time 5 "http://$(ip route | awk '/default/ {print $3}'):9223/json/list"
```

Use the WSL-reachable `webSocketDebuggerUrl` returned by the first curl, for
example:

```bash
playwriter session new --direct ws://172.28.240.1:9223/devtools/browser/<browser-id>
```

If WSL curl returns `Recv failure: Connection reset by peer`, the proxy exists
but Edge is not listening on Windows. Run
`Invoke-RestMethod http://127.0.0.1:9222/json/version` in Windows PowerShell and
relaunch Edge with the exact CDP command until it succeeds.

If Playwriter later reports `ECONNREFUSED 127.0.0.1:9222`, do not use the
Windows-local WebSocket URL. Use the WSL-reachable URL from
`http://<gateway>:9223/json/version`.

## Standard Portal URL

Use this RC Portal URL for sideloaded agent/plugin validation and DevUI
visibility:

```text
https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.AzCopilot_ArgQueryGenerator_plugin=15.0&exp.AzCopilot_ArgQueryRunner_plugin=15.0&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&Microsoft_Azure_Copilot_clientoptimizations=false&feature.customportal=false&feature.canmodifyextensions=true#home
```

If Portal redirects to `/auth/login/`, stop and ask the user to finish sign-in
in the debug Edge window. Then navigate to the same URL again.

## Playwriter CDP Flow

1. Run `playwriter skill`.
2. Print the CDP setup commands above.
3. Verify Windows CDP and WSL proxy.
4. Start a direct CDP Playwriter session using the WSL-reachable browser
   WebSocket URL.
5. List pages and choose the Portal page by URL/title, not a stored target ID.
6. Navigate to the standard Portal URL.
7. Observe with `console.log(state.page.url())` and
   `snapshot({ page: state.page })`.
8. Open Copilot, enable Agent mode, and verify the Agent button is pressed.
9. Open the SideLoad blade directly when sideloading.
10. Register the full agent/plugin manifest.
11. Start a scoped conversation to force tool selection.
12. Capture browser-visible CopilotWeb/DirectLine traffic and correlate with
    DevUI/service logs.

Useful Playwriter commands:

```bash
playwriter -s <session> -e 'console.log(JSON.stringify(browser.contexts().map((c, ci) => ({ context: ci, pages: c.pages().map((p, pi) => ({ page: pi, title: p.title(), url: p.url() })) })), null, 2))'
```

```bash
playwriter -s <session> -e 'state.page = context.pages().find((p) => p.url().includes("portal.azure.com")) ?? context.pages()[0]; console.log("URL:", state.page.url()); console.log(await snapshot({ page: state.page, showDiffSinceLastCall: false }));'
```

## SideLoad Blade

Use the SideLoad blade directly. Do not depend on the Copilot banner. In current
Portal builds, `globalThis.az.openBlade` may not exist on the top page even when
`MsPortalFx` exists, so verify the actual blade UI loaded after any navigation
attempt.

```js
az.openBlade({
	extensionName: 'Microsoft_Azure_Copilot',
	bladeName: 'SideLoad.ReactView',
})
```

Expected hash if routing succeeds:

```text
#view/Microsoft_Azure_Copilot/SideLoad.ReactView
```

If direct hash navigation opens a shell with content title `undefined` or only
shows `Console Error Info`, treat the blade as not loaded. Do not proceed to
registration until the snapshot or target inspection shows the actual SideLoad
UI with Register/Test/Scoped Conversations controls.

Current reliable RC path when direct hash navigation is broken:

1. Open Copilot from the Portal top bar.
2. Inspect CDP iframe targets and identify the Copilot iframe by text such as
   `Test your plugin or agent`.
3. Enable Agent mode in the Copilot iframe.
4. Click `Link to DevUI`. It may not navigate the iframe itself, but it causes
   Portal to load the `Copilot testing`/SideLoad blade and create additional
   sandbox iframe targets.
5. Re-list CDP targets and identify the SideLoad iframe by text such as
   `Plugin & Agent Test`, `Scoped Conversations`, `Test Plugins`, `Register`,
   and `monaco === true`.

Critical target discipline:

- Use exactly one SideLoad iframe target for `Plugin & Agent Test` registration
  and the following `Scoped Conversations` submit.
- Do not register in one sandbox iframe and submit from a sibling sandbox
  iframe. RC Portal can keep multiple live `SideLoad.ReactView` iframe instances
  after reloads, direct hash attempts, or DevUI clicks.
- Before acting, inspect each candidate iframe for `document.body.innerText`,
  buttons, inputs, textareas, and Monaco model value. Pick the one whose current
  state matches the next step.
- If multiple SideLoad targets exist and one has corrupted Monaco content or
  stale scoped form defaults, reload Portal and create a fresh SideLoad target
  before continuing.
- Treat target IDs as per-session only. Never store a target ID in the skill or
  assume `sandbox-3` is always the active SideLoad iframe.

Observed RC target pattern from a working direct CDP run:

- `sandbox-1.reactblade-rc.portal.azure.net` hosted the Copilot sidecar.
- `sandbox-2.reactblade-rc.portal.azure.net` and
  `sandbox-3.reactblade-rc.portal.azure.net` both exposed the SideLoad editor
  after DevUI link flow.
- `sandbox-3` had the cleaner SideLoad text and was suitable for Monaco edits.
- The top Portal page title changed to `Copilot testing - Microsoft Azure` even
  though the top-page blade shell still showed content title `undefined`.
- A later fresh run created `sandbox-5` as the active SideLoad iframe, with old
  `sandbox-*` targets still alive. This is why matching by text/state is
  mandatory.

When Playwriter snapshots show only the Portal top page, inspect
`http://<gateway>:9223/json/list`. Portal sandbox iframes can appear as separate
CDP targets with `type: "iframe"`, `parentId` set to the Portal page target, and
URLs under `sandbox-*.reactblade-rc.portal.azure.net`. Match targets by live
page text/title, not a saved target ID.

Do not create a new Playwriter session against an iframe target WebSocket URL.
In this run,
`playwriter session new --direct ws://.../devtools/page/<iframe-target>`
succeeded, but the first execute failed with
`browserContext.newPage: Cannot read properties of undefined (reading '_page')`.
Use the browser-level Playwriter session for normal actions and raw
CDP/WebSocket inspection for iframe targets when needed.

Raw CDP iframe inspection pattern:

```bash
node -e 'const ws="ws://<gateway>:9223/devtools/page/<iframe-target-id>"; const socket=new WebSocket(ws); let id=0; const pending=new Map(); socket.onmessage=(event)=>{const msg=JSON.parse(event.data); if(msg.id&&pending.has(msg.id)){pending.get(msg.id)(msg); pending.delete(msg.id);}}; function send(method,params={}){return new Promise(resolve=>{const mid=++id; pending.set(mid,resolve); socket.send(JSON.stringify({id:mid,method,params}));});} socket.onopen=async()=>{await send("Runtime.enable"); const res=await send("Runtime.evaluate",{returnByValue:true,expression:"document.body && document.body.innerText"}); console.log(JSON.stringify(res,null,2)); socket.close();};'
```

For `Runtime.evaluate`, use primitive/string return values or inspect the full
CDP response. Object values may appear as `{}` unless serialized explicitly.

Registration rules:

- Paste one complete JSON object with both `AiPlugins` and `AiAgents` arrays.
- Read Monaco markers after paste. A disabled Register button usually means
  schema validation failed.
- Use the model enum accepted by the current validator. If the marker says
  `gpt-5-mini`, use `gpt-5-mini`.
- Treat disabled Register/Test buttons after a successful click as a possible
  post-submit state, then verify with scoped conversation plus DevUI/service
  traces.
- For Bicep agent/plugin scoped testing, a manifest using `model: "gpt-5-mini"`,
  `isLKG: true`, plugin
  `allowedClients: ["Agent:BicepDeploymentDebugAgent", "AzurePortalRCAdvanced:BicepDeploymentDebug"]`,
  and agent `allowedClients: ["AzurePortalRCAdvanced:BicepDeploymentDebug"]`
  validated with no Monaco markers and enabled Register.
- After `Register` succeeds, the same SideLoad iframe can keep `Register`
  disabled even if you later replace the Monaco model with a new manifest. Use a
  fresh SideLoad target for a second manifest/version test rather than assuming
  the button will re-enable.
- A clean registration state is: markers are empty, `Register` was enabled
  before click, click returns successfully, and `Register` is disabled
  afterward. If `Register` was already disabled before click, you did not
  register the current manifest.

Working raw-CDP Monaco pattern for SideLoad:

- Set the editor with
  `monaco.editor.getModels()[0].setValue(JSON.stringify(manifest, null, 2))`.
- Wait briefly, then read `monaco.editor.getModelMarkers({})`.
- Only click Register when markers are empty and the Register button is enabled.
- After a successful Register click, observed state is
  `Register.disabled === true`, `Test Plugins.disabled === true`, and markers
  still empty.
- When switching tabs, do not click `Scoped Conversations` and immediately call
  `monaco.editor.getModels()[0].setValue(...)`; if the tab switch has not
  rendered yet, this can write prompt text into the manifest editor and corrupt
  the registration tab. Always verify the expected inputs/textareas are present
  before filling scoped conversation fields.

Use this CDP expression shape inside the iframe target:

```js
;(() => {
	const value = JSON.stringify(manifest, null, 2)
	const models = monaco.editor.getModels()
	models[0].setValue(value)
	return JSON.stringify({
		modelCount: models.length,
		valueLength: value.length,
	})
})()
```

Validation expression:

```js
;(() =>
	JSON.stringify({
		markers: monaco.editor.getModelMarkers({}).map((m) => ({
			message: m.message,
			severity: m.severity,
			line: m.startLineNumber,
			column: m.startColumn,
		})),
		buttons: Array.from(document.querySelectorAll('button')).map((b, i) => ({
			i,
			text: b.innerText,
			disabled: b.disabled,
		})),
	}))()
```

## Scoped Conversation Rules

Use scoped conversations to force the intended sideloaded agent/plugin.

- Scoped conversations require Agent/Advanced mode.
- The competency client string is `<Client>Advanced:<CompetencyId>`.
- For RC Portal, use `AzurePortalRCAdvanced:<CompetencyId>`.
- Add the exact scoped string to both the agent and plugin `allowedClients`.
- Add `Agent:<AgentName>` to the plugin `allowedClients` so the agent can call
  the plugin.
- Set `isLKG: true` for scoped sideload testing unless intentionally testing
  flights.
- Keep `functions[*].name` aligned with `runtimes[*].run_for_functions`.

Recommended Bicep test competency:

```text
BicepDeploymentDebug
AzurePortalRCAdvanced:BicepDeploymentDebug
```

The scoped nudge should start an agent conversation through:

```text
POST https://copilotweb.canary.production.portalrp.azure.com/api/conversations/start?api-version=2025-08-15
```

Expected body shape:

```json
{
	"conversationType": "Chat",
	"mode": "agent",
	"competency": { "id": "BicepDeploymentDebug", "displayName": "" }
}
```

Observed scoped conversation behavior in RC Portal:

- The SideLoad `Scoped Conversations` tab successfully posts the expected
  `conversationType: "Chat"`, `mode: "agent"`, and `competency.id` to
  `copilotweb.canary.production.portalrp.azure.com/api/conversations/start`.
- The subsequent DirectLine `NudgeMessage` can include an
  `azurecopilot/clientcontext` attachment whose `competency` is `null` and
  `mode` is `chat`. Do not treat that alone as failure if the preceding
  CopilotWeb conversation start had `mode: "agent"` and the expected competency.
- Portal extension telemetry records the scoped nudge competency and prompt
  length under `CopilotManager`/`Unified-Copilot-Nudge`; this is useful when
  DirectLine attachments look misleading.
- Browser-visible `copilotweb` and DirectLine calls prove scoped conversation
  startup and user-turn delivery, but not necessarily HTTP plugin execution.
  Continue to inspect Copilot activity, DevUI, and service logs.
- After clicking `Submit`, verify the Copilot sidecar shows the exact prompt you
  submitted. If it shows a prompt from a previous attempt, you used a stale
  scoped iframe or clicked the wrong submit button.
- If network capture prints no `copilotweb`/DirectLine events but the Copilot
  sidecar updates, your capture was attached to the wrong target set or started
  too late. Re-list targets and capture all Portal page, SideLoad iframe,
  Copilot iframe, and worker targets before submit.
- For the built-in SideLoad scoped form, fill the first `input` and first
  `textarea` under the
  `API: Scoped conversations with custom prompts and competency` section. The
  lower `CopilotTopActions` component has separate default `ArgStorage` controls
  and should not be mistaken for the API submit path unless intentionally
  testing that component.

## AXEAgents Contract

For this repo, the Copilot-facing service is AXEAgents/CnxPlugins.

- First-party app/resource ID: `1dce83cb-ee48-4e43-bd08-a23fd936428e`.
- Portal token acquisition must use
  `Az.getAuthorizationToken({ resourceName: "cnxplugins" })`.
- API requests must pass `Authorization: authToken.header`, not the raw token
  object.
- Stable routes are under `/plugins`.
- Preview routes are under `/preview-plugins`.
- Regional hosts include
  `https://cnxpluginsweb.canary.production.portalrp.azure.com` and
  `https://cnxpluginsweb.production.portalrp.azure.com`.
- Correlate with `x-ms-correlation-id`, `x-ms-conversation-id`,
  `x-ms-client-request-id`, `x-ms-client-session-id`, `x-ms-plugin`,
  `x-ms-mode`, and `x-ms-agent` when present.

## Bicep Plugin Contract

Use the Bicep preview route as the deployment test target.

- Deploy endpoint:
  `POST https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/deploy`.
- Status endpoint:
  `GET https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/subscriptions/{subscription_id}/deployments/{deployment_name}`.
- Auth type: `EntraOnBehalfOf`.
- Auth scope: `1dce83cb-ee48-4e43-bd08-a23fd936428e/.default`.
- Required request fields: `bicep_config`, `subscription_id`, `location`,
  `async_response`, and `messageLocale`.
- `bicep_config.parts[0].data.files` must contain objects with `file_name` and
  `content`.
- Without confirmation, the endpoint returns
  `{"Data":{"Type":"Confirmation","Message":"..."}}` and must not perform side
  effects.
- With `confirmation: true` or `confirmation: "true"`, the endpoint starts
  deployment and returns `202` with `Location` and `Retry-After`.
- Current source sets `Retry-After: 10`, not `30`.
- Current canary test code pins polling `Location` to
  `https://cnxpluginsweb.canary.production.portalrp.azure.com`.
- The mounted preview route is `/preview-plugins/bicep/...`; local isolated unit
  tests mount the same router at root and therefore assert `/bicep/...` paths.
  Prefer source-mounted behavior for real-client manifests.

Minimal request body shape:

```json
{
	"bicep_config": {
		"artifactId": "bicep-op_test",
		"name": "Bicep for Infrastructure plan",
		"parts": [
			{
				"kind": "data",
				"data": {
					"files": [
						{
							"file_name": "main.bicep",
							"content": "resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {}"
						}
					]
				}
			}
		],
		"metadata": { "type": "bicep" }
	},
	"subscription_id": "00000000-0000-0000-0000-000000000000",
	"location": "eastus",
	"async_response": true,
	"messageLocale": "en-US"
}
```

## Network Capture

For Portal Copilot, capture broad browser-visible traffic. Plugin execution may
happen server-side and not appear as a browser request to `cnxpluginsweb`.

Track at least:

- `copilotweb`
- `directline`
- `cnxpluginsweb`
- `/plugins/`
- `/preview-plugins/`
- `conversation`
- `activities`
- `orchestr`
- `plugin`

Important browser-visible calls:

- Scoped conversation start:
  `POST https://copilotweb.canary.production.portalrp.azure.com/api/conversations/start?api-version=2025-08-15`.
- Chat history/status polling:
  `GET https://copilotweb.canary.production.portalrp.azure.com/api/chats?api-version=2025-08-15`.
- User turn delivery:
  `POST https://directline.botframework.com/v3/directline/conversations/<id>/activities`.

Summaries must include status code, URL, request body when useful, `Location`,
`Retry-After`, conversation IDs, and correlation IDs. Redact tokens.

Do not print raw `copilotweb /api/conversations/start` or DirectLine response
bodies. They contain DirectLine bearer tokens. Parse them in-memory, print only
sanitized fields such as conversation ID, mode, competency, chat state, activity
IDs, activity text, attachment names/content types, and token presence booleans.

When summarizing DirectLine activities, never print attachment content for
`azurecopilot/authorization`, DirectLine tokens, or any string matching
`Bearer ` or JWT-looking values. For attachments, prefer
`{ name, contentType, contentKeys }` only.

Avoid `await page.waitForTimeout(10000)` inside a default Playwriter execute
call. It can hit the command execution limit. Use shorter polling loops or
increase the Bash tool timeout if a long wait is necessary.

Do not use top-page `fetch()` to force `copilotweb` polling from
`rc.portal.azure.com`; it can fail with `TypeError: Failed to fetch`. Observe
natural client polling, trigger UI actions, or use captured
DirectLine/CopilotWeb calls instead.

Response-body capture note:

- `Network.getResponseBody` can retrieve `copilotweb` and DirectLine bodies from
  the target that observed the response.
- Always redact DirectLine `token`, `streamUrl`, bearer tokens, and JWT-looking
  strings before printing.
- A typical successful scoped conversation start body includes DirectLine
  endpoint/token metadata, `id` matching the DirectLine conversation ID,
  `type: "Chat"`, and `state: "New"`.

Prompting notes from Bicep scoped testing:

- Tool-forcing prompts with raw JSON arguments or embedded Bicep resource
  declarations can be refused before plugin execution, even when prompt
  telemetry says `notSafe: false`.
- A concise natural-language prompt with a real selected subscription ID and
  simple file content was more likely to select
  `deploy_bicep_debug_configuration` and show Copilot agent activity.
- Avoid fake subscription IDs for final real-client validation; they can bias
  the model/orchestrator toward refusal or error paths before the plugin
  confirmation card renders.
- Avoid placeholder-only Bicep comments for confirmation-card validation if you
  need the endpoint to accept the eventual confirmed retry; they may still be
  enough for tool selection but can result in a function error instead of a
  rendered confirmation card.
- If Copilot activity says `Selected deploy_bicep_debug_configuration` and
  `1 action completed`, but the final text says the prior function call returned
  an error and no card rendered, registration and tool selection likely worked;
  inspect DevUI/service logs for the plugin error details.
- The best observed prompt for tool selection was concise and natural-language,
  with a real selected subscription ID:
  `Deploy my provided Bicep file to subscription <id> in eastus. File main.bicep contains: // confirmation-only placeholder. Show the deployment confirmation first.`
- A prompt using `metadata purpose = 'confirmation only'` was refused in one
  run. Avoid unusual or invalid Bicep snippets when the goal is to validate
  confirmation-card rendering.
- A prompt using `targetScope = 'subscription'` selected the tool/agent but
  still did not render the confirmation card in the observed run.
- Embedding full JSON tool arguments tends to be less reliable than concise
  natural language for the current real client.

## Validation Checklist

- Unit tests for the route and model behavior pass.
- Portal loaded from the debug URL in direct CDP mode.
- Agent mode is enabled before testing agent-backed plugins.
- SideLoad registration succeeds with both agent and plugin present.
- Scoped conversation starts with the intended competency.
- Copilot shows the confirmation card for the first Bicep deploy call.
- Confirmed retry returns `202`, `Location`, and `Retry-After`.
- Polling continues until terminal UI output renders.
- DevUI and/or service logs confirm the expected agent/plugin/function ran.
- Correlation, conversation, and deployment IDs line up across browser traces
  and service logs.

## Common Current Failures

- `Recv failure: Connection reset by peer`: WSL proxy exists, but Edge is not
  listening on Windows `127.0.0.1:9222`.
- `ECONNREFUSED 127.0.0.1:9222`: Playwriter used the Windows-local WebSocket
  URL. Use the WSL-reachable `ws://<gateway>:9223/...` URL.
- Portal lands on `/auth/login/`: user must finish sign-in in the debug Edge
  window.
- Disabled SideLoad Register button: read Monaco markers; fix schema/model enum.
- Scoped conversation starts but plugin does not run: allowedClients mismatch,
  agent did not select the function, prompt was too broad, or policy/safety
  blocked side effects.
- No browser `cnxpluginsweb` request: not necessarily failure; HTTP plugins can
  be invoked server-side by orchestrator.
- Bicep source embedded directly in the scoped kickoff prompt can trigger
  `ContentSafetyClassificationError`. A safer prompt can start the scoped agent
  conversation, but if it omits file content the agent may ask for the file
  instead of calling the plugin. Provide required tool arguments in a
  structured, low-risk form and verify with DirectLine/DevUI whether the
  function was called.
- Direct hash navigation to `#view/Microsoft_Azure_Copilot/SideLoad.ReactView`
  can leave Portal in an `undefined` blade shell. Use Copilot Agent mode plus
  `Link to DevUI`, then find the SideLoad sandbox iframe by CDP target text.
- The `Test your plugin or agent` banner can remain inert. Do not block on it if
  `Link to DevUI` and SideLoad iframe registration work.
- Scoped conversation start can succeed while DirectLine
  `azurecopilot/clientcontext` still reports `mode: "chat"` and
  `competency: null`; trust the `copilotweb /api/conversations/start` body for
  scoped startup and use activity/DevUI/service evidence for plugin execution.
- Copilot may select the Bicep deployment function but render a generic final
  failure instead of a confirmation card. Treat that as a plugin
  execution/debugging problem, not a SideLoad registration failure, and
  correlate through DevUI/service logs.
- Multiple live SideLoad iframes can make the run look correct while it is not:
  one iframe may contain the registered manifest, another may contain the scoped
  form, and another may contain stale defaults. Always perform Register and
  Submit from the same verified SideLoad target.
- If Monaco content starts with the scoped prompt followed by JSON, the prompt
  was accidentally written into the manifest editor. Discard that target and
  start fresh.
- If `Register` is disabled before a new manifest registration click, the
  current manifest was not registered in that target. Start fresh or use a new
  version/name in a fresh SideLoad instance.
- If Copilot says `Sorry, I can't help with that` with no activity details,
  likely causes are stale/missing scoped registration, prompt refusal, or wrong
  scoped competency. Verify the CopilotWeb start body, the SideLoad target's
  registered manifest, and Copilot activity.
- If Copilot shows `1 action completed` and activity names the Bicep deployment
  function/agent but no confirmation card appears, the scoped registration and
  tool selection path worked. The next investigation is plugin invocation
  details in DevUI/service logs, especially Lua payload shape and endpoint
  response/error.

## Local Docs

Use local PortalFx docs only when the current workflow needs source
confirmation:

- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/plugin-e2e-setup.md`
- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/agents-sideloading.md`
- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/scoped-conversations-copilot.md`
- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/direct-agent-invocation.md`
- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/http-confirmation.md`
- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/develop-httpplugin.md`
- `/home/ariaamini/AzureUX-PortalFx/docs-internal/product/copilot/long-running-operations-contract.md`

## Cleanup

Close the temporary debug Edge window when finished. If desired, remove the WSL
proxy and firewall rule from an elevated Windows PowerShell:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=9223
Remove-NetFirewallRule -DisplayName "Edge CDP from WSL"
```
