#!/usr/bin/env bash
#MISE description="Bootstrap a fresh clone"

set -euo pipefail

cd "$(dirname "$0")/.."

mise install
vp i
vp exec varlock load

mise run setup
vp run compose:up
vp run db:migrate

echo
echo "Bootstrap complete. Run 'vp dev' to start the app."
