#!/usr/bin/env bash
set -euo pipefail
cd $HOME

# stow
rm .zshrc
sudo apt install stow -yq
stow -v --target $HOME --dir "$HOME/dotfiles" .

# zsh
sudo apt install zsh -yq
sudo chsh -s "$(which zsh)" $USER

# nix
[[ ! -e .config/nix/nix.conf ]] && cp dotfiles/dot-config/nix/nix.conf .config/nix/nix.conf
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . /home/aamini.linux/.nix-profile/etc/profile.d/nix.sh
fi

# mise
export PATH="$PATH:$HOME/.local/bin"
export MISE_QUIET=1
curl https://mise.run | sh
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i
