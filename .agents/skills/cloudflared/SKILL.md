---
name: cloudflared
description:
  Run and debug the local Bicep HTTP API through a Cloudflare tunnel. Use for
  local /preview-plugins/bicep/deploy LRO testing, worker pickup, polling,
  Portal Copilot SideLoad, or local HTTP e2e failures.
---

# Cloudflared Bicep E2E

Work from `pysrc/WorkloadsAssistantCore`.

Check before starting duplicates:

```bash
ss -ltnp '( sport = :2750 )'
ss -ltnp '( sport = :2751 )'
curl -sS http://127.0.0.1:2750/healthcheck
```

Run API and worker in separate long-running shells. The API only submits LRO
jobs; the worker must also be running or polls will stay `202 InProgress`.

```bash
mise trust
mise install
mise run install
mise run dev
```

```bash
APP_MODE=worker mise exec -- uv run python -m src.start_server
```

Run tunnel:

```bash
mise x cloudflared@2026.3.0 -- cloudflared tunnel --url http://127.0.0.1:2750
```

Set URL:

```bash
export TUNNEL_URL="https://*.trycloudflare.com"
curl -fsS "$TUNNEL_URL/healthcheck"
```

Run bicep HTTP e2e:

```bash
export AZURE_TENANT_ID="..."
export AZURE_SUBSCRIPTION_ID="..."
BASE_URL="$TUNNEL_URL/preview-plugins" mise run test:http --target local -v
```

Copilot endpoint:

```text
$TUNNEL_URL/preview-plugins/bicep/deploy
```

Manual poll for a captured deployment id:

```bash
token=$(az account get-access-token --tenant "$AZURE_TENANT_ID" --resource https://management.azure.com/ --query accessToken -o tsv)
curl -sS -H "Authorization: Bearer $token" \
  "$TUNNEL_URL/preview-plugins/bicep/subscriptions/$AZURE_SUBSCRIPTION_ID/deployments/$DEPLOYMENT_ID?locale=en"
```

Verify ARM terminal state:

```bash
az deployment sub show \
  --subscription "$AZURE_SUBSCRIPTION_ID" \
  --name "$DEPLOYMENT_ID" \
  --query '{name:name,state:properties.provisioningState,timestamp:properties.timestamp}' \
  --output json
```

Useful signals:

- `POST /bicep/deploy` must return `202` with `Location` pointing at `/bicep/subscriptions/{sub}/deployments/{uuid}`.
- First GETs may return `202 InProgress`; terminal success returns `200 Succeeded` with deployment artifacts.
- Progress thoughts prove worker pickup: `Compiling bicep templates...`, `Submitting deployment to ARM...`, `Deployment accepted by ARM.`
- If POST succeeds but polling never advances, check that the worker process is running and inspect worker logs for `poll_trigger` and `BicepDeploymentCallbackV1 invoked`.
- `Retry-After` is configurable via `BICEP_POLLING_RETRY_AFTER`; tests should not hard-code `10`.

Focused tests:

```bash
uv run pytest tests/http_plugins/bicep/test_bicep_router.py tests/http_plugins/bicep/test_bicep_legacy_router.py tests/lro/test_bicep_deployment_callback.py
```
