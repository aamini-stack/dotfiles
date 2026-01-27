#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Nix is installed
if ! command -v nix &> /dev/null; then
    echo "Nix not found. Please install nix at: https://nixos.org/nix/install"
    exit 0
fi

echo "Running stow to symlink dotfiles..."
cd "$SCRIPT_DIR"
LC_ALL=C stow -v --target="$HOME" --dotfiles .

echo "Installing dotfiles profile..."
nix profile add "${SCRIPT_DIR}/scripts/nix#default"

echo "Done!"
echo "Run 'nix flake update && nix profile upgrade dotfiles' to upgrade packages later."
