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
command -v zsh | sudo tee -a /etc/shells
STATUS="$(passwd --status $USER | awk '{print $2}')"
if [[ $STATUS = 'L' ]]; then
  echo "User has no password. Please set one as it is required to change the default shell to zsh"
  sudo passwd $USER 
fi
echo "Changing Shell"
chsh -s "$(which zsh)" "$USER"
