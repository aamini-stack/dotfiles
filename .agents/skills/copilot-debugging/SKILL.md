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
.agents/copilot-debugging/bicep-deployment-debug.manifest.json
```

For local tunnel tests, replace the manifest runtime URL with:

```text
$TUNNEL_URL/preview-plugins/bicep/deploy
```

SideLoad flow:

```text
If testing local code, start API + cloudflared and patch manifest URL.
Register tab -> paste manifest -> Register
Scoped Conversations tab -> upper API form only
Competency: BicepDeploymentDebug
Prompt: Deploy the built-in Bicep debug sample to subscription <subscription-id> in eastus. Use deployment label copilot-bicep-debug. Show the deployment confirmation first.
Submit -> approve confirmation -> wait for LRO output
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
Use direct CDP, not extension mode.
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
Disabled Register -> inspect Monaco markers; if empty, reload and use a fresh SideLoad blade.
```

Cleanup:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=9223
Remove-NetFirewallRule -DisplayName "Edge CDP from WSL"
```
