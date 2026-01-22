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
LC_ALL=C stow -v --target="$HOME" .

# Install/upgrade dotfiles tools via Nix
echo "Installing dotfiles tools via Nix..."
if nix profile list | grep -q "dotfiles"; then
    echo "Dotfiles profile found, upgrading..."
    nix profile upgrade dotfiles
else
    echo "Installing dotfiles profile..."
    nix profile add "${SCRIPT_DIR}#default"
fi

echo "Done!"
echo "Run 'nix flake update && nix profile upgrade dotfiles' to upgrade packages later."
