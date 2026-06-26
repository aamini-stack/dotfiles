---
name: cloudflared
description:
  Run the local Bicep HTTP API through a Cloudflare tunnel for Portal Copilot
  SideLoad and local HTTP e2e testing. Use when a local endpoint must be
  reachable from Azure Portal Copilot.
---

# Cloudflared Bicep E2E

Run API:

```bash
cd pysrc/WorkloadsAssistantCore
mise trust
mise install
mise run install
mise run dev
```

Run tunnel:

```bash
cd pysrc/WorkloadsAssistantCore
mise x cloudflared@2026.3.0 -- cloudflared tunnel --url http://127.0.0.1:2750
```

Set URL:

```bash
export TUNNEL_URL="https://*.trycloudflare.com"
curl -fsS "$TUNNEL_URL/healthcheck"
```

Run bicep HTTP e2e:

```bash
export ARM_TENANT_ID="..."
export ARM_SUBSCRIPTION_ID="..."
BASE_URL="$TUNNEL_URL/preview-plugins" mise run test:http --target local
```

Copilot endpoint:

```text
$TUNNEL_URL/preview-plugins/bicep/deploy
```
