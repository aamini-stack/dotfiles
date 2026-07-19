#!/usr/bin/env bash
set -euo pipefail

ws="${HERDR_WORKSPACE_ID:?HERDR_WORKSPACE_ID not set}"

if [[ -n "${HERDR_PANE_ID:-}" ]]; then
  pane_json=$("$HERDR_BIN_PATH" pane get "$HERDR_PANE_ID")
else
  pane_json=$("$HERDR_BIN_PATH" pane current)
fi
cwd=$(printf '%s' "$pane_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"]["cwd"])')

dir="$HERDR_PLUGIN_CONFIG_DIR"
mkdir -p "$dir"
file="$dir/roots"
touch "$file"
awk -F'\t' -v id="$ws" '$1 != id' "$file" > "$file.tmp"
printf '%s\t%s\n' "$ws" "$cwd" >> "$file.tmp"
mv "$file.tmp" "$file"

"$HERDR_BIN_PATH" notification show "cd guard root set" --body "$cwd"
