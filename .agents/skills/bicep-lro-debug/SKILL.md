---
name: bicep-lro-debug
description:
  Verify and debug the local Bicep LRO deploy router end-to-end. Use when
  running local /preview-plugins/bicep/deploy in LRO mode, testing worker
  pickup, polling status, or diagnosing deploy e2e failures.
---

# Bicep LRO Debug

Work from `pysrc/WorkloadsAssistantCore`.

Run API + worker:

```bash
mise run dev
APP_MODE=worker mise exec -- uv run python -m src.start_server
```

Check existing processes before starting duplicates:

```bash
ss -ltnp '( sport = :2750 )'
ss -ltnp '( sport = :2751 )'
curl -sS http://127.0.0.1:2750/healthcheck
```

Run deploy e2e:

```bash
mise run test:http --target local -v
```

Manual poll for a captured deployment id:

```bash
token=$(az account get-access-token --tenant "$AZURE_TENANT_ID" --resource https://management.azure.com/ --query accessToken -o tsv)
curl -sS -H "Authorization: Bearer $token" \
  "http://localhost:2750/preview-plugins/bicep/subscriptions/$AZURE_SUBSCRIPTION_ID/deployments/$DEPLOYMENT_ID?locale=en"
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
- `Retry-After` is configurable via `BICEP_POLLING_RETRY_AFTER`; tests should not hard-code `10`.

Focused tests:

```bash
uv run pytest tests/http_plugins/bicep/test_bicep_router.py tests/http_plugins/bicep/test_bicep_legacy_router.py tests/lro/test_bicep_deployment_callback.py
```
