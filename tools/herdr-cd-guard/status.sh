#!/usr/bin/env bash
set -euo pipefail

ws="${HERDR_WORKSPACE_ID:?HERDR_WORKSPACE_ID not set}"
dir="$HERDR_PLUGIN_CONFIG_DIR"

root=""
if [[ -f "$dir/roots" ]]; then
  root=$(awk -F'\t' -v id="$ws" '$1 == id {print $2; exit}' "$dir/roots")
fi

if [[ -z "$root" ]]; then
  "$HERDR_BIN_PATH" notification show "cd guard: unmanaged" --body "open via wt switch to enable"
  exit 0
fi

state="enabled"
if [[ -f "$dir/disabled" ]] && grep -qxF "$ws" "$dir/disabled"; then
  state="disabled"
fi

"$HERDR_BIN_PATH" notification show "cd guard: $state" --body "root: $root"
