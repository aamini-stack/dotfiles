#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $SCRIPT_DIR/..

sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
. ~/.nix-profile/etc/profile.d/nix.sh
./install.sh
sudo chsh -s $(which zsh) $USER
