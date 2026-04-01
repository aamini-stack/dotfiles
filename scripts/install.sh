#!/usr/bin/env bash
set -euo pipefail

# nix
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
. /home/aamini.linux/.nix-profile/etc/profile.d/nix.sh

# mise
mkdir -p ~/.config/mise
ln -s ~/dotfiles/dot-config/mise/config.toml ~/.config/mise/config.toml
mkdir -p ~/.config/nix
ln -s ~/dotfiles/dot-config/nix/nix.conf ~/.config/nix/nix.conf
curl https://mise.run | sh
mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i 

rm -r ~/.config/mise
rm -r ~/.config/nix
stow -v --dir="$HOME/dotfiles" --target "$HOME"
