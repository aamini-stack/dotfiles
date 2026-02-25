#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname -- "$0"; )" && pwd; )"
REPO_DIR="$( cd "$SCRIPT_DIR/.." && pwd; )"
NIX_SH="$HOME/.nix-profile/etc/profile.d/nix.sh"

if ! command -v nix >/dev/null 2>&1; then
  if [ -r "$NIX_SH" ]; then
    . "$NIX_SH"
  fi
fi

if ! command -v nix >/dev/null 2>&1; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon --no-modify-profile
  . "$NIX_SH"
fi

cd "$REPO_DIR"
nix profile add ".#default" --extra-experimental-features nix-command --extra-experimental-features flakes

./scripts/stow.sh

# Change default shell
rm -f ~/.bash_profile
cat > ~/.bash_profile <<EOF
export SHELL=`which zsh`
if [ -x $SHELL ]; then
  exec "$SHELL" -l
fi
EOF
