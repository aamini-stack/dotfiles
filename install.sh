#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Nix is installed
if ! command -v nix &> /dev/null; then
    echo "Nix not found. Installing Nix..."
    curl -L https://nixos.org/nix/install | sh -s -- --daemon
    echo "Please restart your shell and run this script again."
    exit 0
fi

echo "Running stow to symlink dotfiles..."
cd "$SCRIPT_DIR"
stow -v --target="$HOME" .

echo "Installing dotfiles tools via Nix..."
nix profile add "${SCRIPT_DIR}#default"

echo "Done! Tools installed and dotfiles linked."
