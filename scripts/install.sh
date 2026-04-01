#!/usr/bin/env bash
set -euo pipefail
cd $HOME

sudo apt install zsh

# nix
mkdir -p .config/nix
[[ ! -e .config/nix/nix.conf ]] && cp dotfiles/dot-config/nix/nix.conf .config/nix/nix.conf
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
fi
. /home/aamini.linux/.nix-profile/etc/profile.d/nix.sh

# mise
export PATH="$PATH:$HOME/.local/bin"
mkdir -p .config/mise
[[ ! -e .config/mise/config.toml ]] && cp ~/dotfiles/dot-config/mise/config.toml .config/mise/config.toml
curl https://mise.run | sh
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i --silent

[[ ! -e .zshrc ]] && cp dotfiles/dot-zshrc .zshrc

cd dotfiles
stow -v --dotfiles --adopt .
