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

# Ensure flakes are enabled
if ! nix flake --help &> /dev/null 2>&1; then
    echo "Enabling Nix flakes..."
    mkdir -p ~/.config/nix
    echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
fi

echo "Installing dotfiles tools via Nix..."
nix profile install "${SCRIPT_DIR}#default"

echo "Running stow to symlink dotfiles..."
cd "$SCRIPT_DIR"
stow -v --target="$HOME" .

echo "Done! Tools installed and dotfiles linked."
