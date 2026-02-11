#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing dotfiles profile..."
nix profile add "${SCRIPT_DIR}#default" --extra-experimental-features nix-command --extra-experimental-features flakes

echo "Running stow to symlink dotfiles..."
cd "$SCRIPT_DIR"
LC_ALL=C stow -v --target="$HOME" --dotfiles .

echo "Run 'nix flake update && nix profile upgrade dotfiles' to upgrade packages later."
