#!/usr/bin/env bash
set -euo pipefail

ws="${HERDR_WORKSPACE_ID:?HERDR_WORKSPACE_ID not set}"
dir="$HERDR_PLUGIN_CONFIG_DIR"
mkdir -p "$dir"
file="$dir/disabled"
touch "$file"

if grep -qxF "$ws" "$file"; then
  { grep -vxF "$ws" "$file" || true; } > "$file.tmp"
  mv "$file.tmp" "$file"
  "$HERDR_BIN_PATH" notification show "cd guard: on" --body "workspace $ws"
else
  printf '%s\n' "$ws" >> "$file"
  "$HERDR_BIN_PATH" notification show "cd guard: off" --body "workspace $ws"
fi
