#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname -- "$0"; )" && pwd; )"
if ! command -v nix >/dev/null 2>&1; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . "$HOME/.nix-profile/etc/profile.d/nix.sh"
fi
nix profile add ".#default" --extra-experimental-features nix-command --extra-experimental-features flakes

./scripts/stow.sh

# Change default shell
command -v zsh | sudo tee -a /etc/shells
STATUS="$(passwd --status $USER | awk '{print $2}')"
if [[ $STATUS = 'L' ]]; then
  echo "User has no password. Please set one as it is required to change the default shell to zsh"
  sudo passwd $USER 
fi
echo "Changing Default Shell (Please Enter Password)"
sudo chsh -s "$(which zsh)" "$USER"
