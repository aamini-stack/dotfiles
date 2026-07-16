#!/usr/bin/env bash
set -euo pipefail

# Make user-local tools (mise shims/binaries, worktrunk scripts, etc.) available.
# Herdr's plugin env inherits the server PATH, which may not include shell-profile additions.
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

PARSE_EVENT=$(python3 -c "
import json, os, sys
raw = os.environ.get('HERDR_PLUGIN_EVENT_JSON', '{}')
try:
    data = json.loads(raw)
    payload = data.get('data') if isinstance(data, dict) else data
    if not isinstance(payload, dict):
        payload = data
    workspace = payload.get('workspace', {}) if isinstance(payload, dict) else {}
    worktree = payload.get('worktree', {}) if isinstance(payload, dict) else {}
    print(workspace.get('workspace_id', ''))
    print(worktree.get('path', ''))
except Exception as e:
    print(f'parse error: {e}', file=sys.stderr)
    sys.exit(1)
")

WORKSPACE_ID=$(printf '%s' "$PARSE_EVENT" | sed -n '1p')
WORKTREE_PATH=$(printf '%s' "$PARSE_EVENT" | sed -n '2p')

if [[ -z "$WORKTREE_PATH" ]]; then
  log "no worktree path in event payload ($EVENT_NAME); skipping"
  exit 0
fi

if [[ ! -d "$WORKTREE_PATH" ]]; then
  log "worktree path does not exist: $WORKTREE_PATH"
  exit 0
fi

log "event=$EVENT_NAME worktree=$WORKTREE_PATH"

# Herdr already created the workspace for this worktree; make sure it is focused
# so the UI jumps to the new worktree.
if [[ -n "$WORKSPACE_ID" ]]; then
  herdr workspace focus "$WORKSPACE_ID" 2>/dev/null || true
fi

log "worktree workspace focused"
