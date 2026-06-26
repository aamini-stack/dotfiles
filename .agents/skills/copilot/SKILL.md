---
name: copilot-debugging
description:
  Debug the Bicep HTTP plugin in real Azure Portal Copilot with SideLoad and
  Playwriter direct CDP.
---

# Copilot Bicep Debugging

Use the real Portal Copilot client to verify SideLoad registration, plugin
routing, confirmation cards, auth, and LRO polling for the Bicep deploy API.

For local API/worker verification and tunnel setup before involving Portal,
use the `cloudflared` skill first.

## Manual Setup

1. Launch Edge from Windows PowerShell:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="$env:TEMP\edge-copilot-debug"
```

2. If running from WSL and CDP is not reachable, add the portproxy from elevated
   Windows PowerShell:

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9223 connectaddress=127.0.0.1 connectport=9222
New-NetFirewallRule -DisplayName "Edge CDP from WSL" -Direction Inbound -LocalPort 9223 -Protocol TCP -Action Allow
```

## Connect Playwriter

Use direct CDP for this skill. Portal SideLoad and Copilot run in sandboxed
cross-origin React blade frames, and extension mode has been unreliable there.

```bash
GW=$(ip route | awk '/default/ {print $3; exit}')
WS_URL=$(node -e 'fetch(process.argv[1]).then(r => r.json()).then(j => console.log(j.webSocketDebuggerUrl))' "http://${GW}:9223/json/version")
playwriter session new --direct "${WS_URL}"
```

## Supervised Smoke Test

Run one small snippet per step. Each snippet stores or reuses `state.bicepDebug`,
so failed steps can be inspected, edited, and rerun without starting over.

Edit the constants in step 1. Avoid relying on shell environment variables for
snippet inputs; Playwriter sessions can outlive the shell command that invoked
them.

Available manifests:

- `/home/ariaamini/.agents/skills/copilot/manifests/bicep-valid.manifest.json`
- `/home/ariaamini/.agents/skills/copilot/manifests/bicep-invalid.manifest.json`

### 1. Open SideLoad

```bash
playwriter -s <session-id> --timeout 120000 -e "$(cat <<'JS'
const portalUrl = "https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&feature.customportal=false&feature.canmodifyextensions=true#view/Microsoft_Azure_Copilot/SideLoad.ReactView";
const mode = "valid"; // Change to "invalid" for compile-error testing.
state.bicepDebug = {
  subscriptionId: "<subscription-id>",
  location: "eastus",
  deployUrl: "https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/deploy",
  manifestPath: `/home/ariaamini/.agents/skills/copilot/manifests/bicep-${mode}.manifest.json`,
  mode,
  label: `copilot-bicep-${mode}-${Date.now()}`,
  serviceScope: "1dce83cb-ee48-4e43-bd08-a23fd936428e/.default",
  screenshotPath: "/tmp/copilot-bicep-debug.png",
};
if (state.bicepDebug.subscriptionId === "<subscription-id>") throw new Error("Set subscriptionId in step 1.");
state.page = context.pages().find((p) => p.url().startsWith("https://rc.portal.azure.com/")) || (await context.newPage());
await state.page.goto(portalUrl, { waitUntil: "domcontentloaded" });
console.log(JSON.stringify(state.bicepDebug, null, 2));
JS
)"
```

### 2. Install Helpers

```bash
playwriter -s <session-id> --timeout 120000 -e "$(cat <<'JS'
state.bicepDebugHelpers = {
  affirmativeButton: /^(approve|confirm|yes|yes, deploy)$/i,
  negativeButton: /^(cancel|deny|no)$/i,
  async findFrameByText(text, timeoutMs = 90000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    for (const frame of state.page.frames()) {
      try {
        const body = await frame.locator("body").innerText({ timeout: 1000 });
        if (body.includes(text)) return frame;
      } catch {}
    }
    await state.page.waitForTimeout(1000);
  }
  throw new Error(`Timed out waiting for frame containing: ${text}`);
  },
  async findFrameByPredicate(predicate, description, timeoutMs = 150000) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      for (const frame of state.page.frames()) {
        try {
          const body = await frame.locator("body").innerText({ timeout: 1000 });
          if (await predicate(frame, body)) return frame;
        } catch {}
      }
      await state.page.waitForTimeout(1000);
    }
    throw new Error(`Timed out waiting for frame: ${description}`);
  },
  async waitForEnabledButton(frame, text, timeoutMs = 30000) {
    const button = frame.locator("button").filter({ hasText: text });
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      if ((await button.count()) > 0 && (await button.first().isEnabled())) return button.first();
      await state.page.waitForTimeout(1000);
    }
    throw new Error(`Timed out waiting for enabled button: ${text}`);
  },
  async sideLoadFrame(tabName = "Plugin & Agent Test") {
    const frame = await this.findFrameByText(tabName);
    await frame.getByRole("tab", { name: tabName }).click();
    return frame;
  },
};
console.log("BICEP_DEBUG_HELPERS_READY");
JS
)"
```

### 3. Find SideLoad Frame

```bash
playwriter -s <session-id> --timeout 120000 -e "$(cat <<'JS'
const sideLoadFrame = await state.bicepDebugHelpers.sideLoadFrame("Plugin & Agent Test");
console.log("SIDELOAD_FRAME_READY");
JS
)"
```

### 4. Paste Manifest

```bash
MANIFEST_PATH="/home/ariaamini/.agents/skills/copilot/manifests/bicep-valid.manifest.json"
playwriter -s <session-id> --timeout 120000 -e "$(node - "$MANIFEST_PATH" <<'NODE'
const fs = require("node:fs");
const manifestSource = JSON.stringify(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write([
  "const cfg = state.bicepDebug;",
  "const frame = await state.bicepDebugHelpers.sideLoadFrame(\"Plugin & Agent Test\");",
  "function buildManifest() {",
  "  // Playwriter's direct-CDP sandbox cannot read arbitrary files. The shell",
  "  // reads the manifest and injects it here as a JavaScript string literal.",
  `  const manifest = JSON.parse(${manifestSource});`,
  "  manifest.AiAgents = manifest.AiAgents || [];",
  "  const runtime = manifest.AiPlugins[0].manifest.runtimes[0];",
  "  const spec = runtime.spec[0];",
  "  runtime.auth.scopes = [cfg.serviceScope];",
  "  spec.url = cfg.deployUrl;",
  "  spec.script = spec.script",
  "    .replace(/local label = response\\.deployment_label or '[^']*'/, \"local label = response.deployment_label or '\" + cfg.label + \"'\")",
  "    .replace(/name: 'rg-[^']*'/, \"name: 'rg-\" + cfg.label + \"'\")",
  "    .replace(/location = response\\.location or '[^']*'/, \"location = response.location or '\" + cfg.location + \"'\");",
  "  return JSON.stringify(manifest, null, 2);",
  "}",
  "async function getMonacoText() {",
  "  return await frame.evaluate(() => globalThis.monaco?.editor?.getModels?.().map((model) => model.getValue()).join(\"\\n---MODEL---\\n\") || \"\");",
  "}",
  "const manifestText = buildManifest();",
  "const editor = frame.locator(\".monaco-editor\").first();",
  "await editor.waitFor({ state: \"visible\", timeout: 30000 });",
  "await editor.click();",
  "await state.page.context().grantPermissions([\"clipboard-read\", \"clipboard-write\"], { origin: \"https://rc.portal.azure.com\" });",
  "await state.page.evaluate(async (text) => navigator.clipboard.writeText(text), manifestText);",
  "await state.page.keyboard.press(\"Control+A\");",
  "await state.page.keyboard.press(\"Control+V\");",
  "await frame.evaluate((text) => {",
  "  // Clipboard paste updates Monaco, but the SideLoad page may not enable",
  "  // Register until Monaco emits its normal model-change path.",
  "  const model = globalThis.monaco?.editor?.getModels?.()[0];",
  "  if (!model) throw new Error(\"Monaco model not found\");",
  "  model.setValue(text);",
  "}, manifestText);",
  "const expected = [\"BicepDeploymentDebug_plugin\", cfg.serviceScope, cfg.deployUrl, cfg.label];",
  "const started = Date.now();",
  "let verified = false;",
  "while (Date.now() - started < 30000) {",
  "  const modelText = await getMonacoText();",
  "  if (expected.every((marker) => modelText.includes(marker))) {",
  "    verified = true;",
  "    break;",
  "  }",
  "  await state.page.waitForTimeout(1000);",
  "}",
  "if (verified) {",
  "  console.log(\"MANIFEST_PASTE_VERIFIED\");",
  "} else {",
  "  throw new Error(\"Manifest paste verification failed. Monaco preview: \" + (await getMonacoText()).slice(0, 1200));",
  "}",
].join("\n"));
NODE
)"
```

### 5. Register

```bash
playwriter -s <session-id> --timeout 60000 -e "$(cat <<'JS'
const frame = await state.bicepDebugHelpers.sideLoadFrame("Plugin & Agent Test");
await (await state.bicepDebugHelpers.waitForEnabledButton(frame, /^Register$/)).click();
await state.page.waitForTimeout(8000);
console.log("REGISTER_CLICKED");
JS
)"
```

### 6. Submit Scoped Conversation

```bash
playwriter -s <session-id> --timeout 60000 -e "$(cat <<'JS'
const cfg = state.bicepDebug;
const frame = await state.bicepDebugHelpers.sideLoadFrame("Scoped Conversations");
await frame.locator("input").nth(0).fill("BicepDeploymentDebug");
await frame.locator("textarea").nth(0).fill(`Prepare the built-in Bicep debug deployment confirmation card for subscription ${cfg.subscriptionId} in ${cfg.location}. Use deployment label ${cfg.label}.`);
await frame.locator("button").filter({ hasText: /^Submit$/ }).click();
console.log(`SUBMITTED_LABEL=${cfg.label}`);
JS
)"
```

### 7. Find Confirmation

This is the supervised stop. Inspect the real card before approving.

```bash
playwriter -s <session-id> --timeout 180000 -e "$(cat <<'JS'
const cfg = state.bicepDebug;
const helpers = state.bicepDebugHelpers;
const copilotFrame = await helpers.findFrameByPredicate(async (frame, body) => {
  if (!body.includes(cfg.label)) return false;
  if (/Type "confirm" to proceed|Planned deployment details|Deployment confirmation|Are you sure you want to deploy|will not make any changes until you confirm/i.test(body)) return true;
  const yes = await frame.locator("button").filter({ hasText: helpers.affirmativeButton }).count();
  const no = await frame.locator("button").filter({ hasText: helpers.negativeButton }).count();
  return yes > 0 && no > 0;
}, `Copilot confirmation for ${cfg.label}`);
const body = await copilotFrame.locator("body").innerText({ timeout: 5000 });
console.log(body.slice(-3000));
await state.page.screenshot({ path: cfg.screenshotPath, scale: "css", fullPage: true });
console.log(`CONFIRMATION_READY label=${cfg.label} screenshot=${cfg.screenshotPath}`);
JS
)"
```

### 8. Approve And Wait

Only run after the human has inspected the confirmation card.

```bash
playwriter -s <session-id> --timeout 360000 -e "$(cat <<'JS'
const cfg = state.bicepDebug;
const helpers = state.bicepDebugHelpers;
const frame = await helpers.findFrameByPredicate(async (frame, body) => {
  if (!body.includes(cfg.label)) return false;
  const yes = await frame.locator("button").filter({ hasText: helpers.affirmativeButton }).count();
  return yes > 0;
}, `approval button for ${cfg.label}`);
const approve = frame.locator("button").filter({ hasText: helpers.affirmativeButton }).first();
await approve.click();
const started = Date.now();
let last = "";
while (Date.now() - started < 300000) {
  last = await frame.locator("body").innerText({ timeout: 5000 });
  if (/Succeeded|Deployment failed|Failed|Error executing function|Sorry, I wasn't able|Sorry, I can't help/i.test(last)) break;
  await state.page.waitForTimeout(10000);
}
console.log(last.slice(-6000));
await state.page.screenshot({ path: state.bicepDebug.screenshotPath, scale: "css", fullPage: true });
console.log(`FINAL_SCREENSHOT=${state.bicepDebug.screenshotPath}`);
JS
)"
```

## Expected Results

Confirmation card should mention:

```text
Are you sure you want to deploy this Bicep configuration?
Subscription: <subscription-id>
Location: eastus
Files: 1 file(s) - main.bicep
```

Successful final output should include:

```text
Compiling bicep templates...
Submitting deployment to ARM...
Deployment accepted by ARM.
rg-<deployment-label> - Succeeded
```

`Deployment accepted by ARM` alone is not success; wait for a terminal
`Succeeded` or `Failed` result.

## Fast Diagnosis

- Tool error before confirmation: check manifest auth scope. Deployed canary
  must use `1dce83cb-ee48-4e43-bd08-a23fd936428e/.default`, not ARM.
- Storage or ArgStorage response: the lower form was used, or the upper
  competency did not update to `BicepDeploymentDebug`.
- `Reasoning complete` plus tool error: the plugin was selected and invoked;
  debug auth/routing/API logs, not confirmation locators.
- No local tunnel/API request for the fresh label: SideLoad registration is
  stale or the manifest still points at canary.

## Cleanup

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=9223
Remove-NetFirewallRule -DisplayName "Edge CDP from WSL"
```
