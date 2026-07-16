#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$HOME/.config/worktrunk/bin:$HOME/.nix-profile/bin:/opt/nvim-linux-x86_64/bin:$PATH"

LOG_DIR="${HERDR_PLUGIN_STATE_DIR:-/tmp}"
LOG_FILE="$LOG_DIR/wt-hooks.log"
EVENT_NAME="${HERDR_PLUGIN_EVENT:-unknown}"

mkdir -p "$LOG_DIR"

log() {
  local line
  line=$(printf '%s [%s] %s' "$(date -Iseconds)" "wt-hooks" "$*")
  echo "$line" >> "$LOG_FILE"
  echo "$line" >&2
}

if command -v wt >/dev/null 2>&1; then
  WT="wt"
elif command -v mise >/dev/null 2>&1; then
  WT="mise x -- wt"
else
  log "wt not found in PATH and mise is unavailable; skipping"
  exit 1
fi

WORKTREE_PATH=$(python3 -c "
import json, os, sys
raw = os.environ.get('HERDR_PLUGIN_EVENT_JSON', '{}')
try:
    data = json.loads(raw)
    payload = data.get('data') if isinstance(data, dict) else data
    if not isinstance(payload, dict):
        payload = data
    worktree = payload.get('worktree', {}) if isinstance(payload, dict) else {}
    print(worktree.get('path', '') if isinstance(worktree, dict) else '')
except Exception as e:
    print(f'parse error: {e}', file=sys.stderr)
    sys.exit(1)
")

if [[ -z "$WORKTREE_PATH" ]]; then
  log "no worktree path in event payload ($EVENT_NAME); skipping"
  exit 0
fi

if [[ ! -d "$WORKTREE_PATH" ]]; then
  log "worktree path does not exist: $WORKTREE_PATH"
  exit 0
fi

log "event=$EVENT_NAME worktree=$WORKTREE_PATH wt_cmd=$WT"

log "running wt hook pre-remove in $WORKTREE_PATH"
if ! $WT -C "$WORKTREE_PATH" hook pre-remove --yes; then
  STATUS=$?
  log "pre-remove failed with status $STATUS"
  exit "$STATUS"
fi

log "running wt hook post-remove in $WORKTREE_PATH"
$WT -C "$WORKTREE_PATH" hook post-remove --yes
log "post-remove invoked"
