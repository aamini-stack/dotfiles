#!/usr/bin/env bash
set -euo pipefail
cd $HOME

# stow
sudo apt install stow -y
stow -v --dotfiles --adopt .

sudo apt install zsh -y
if getent passwd "$USER" >/dev/null; then
    sudo passwd "$USER"
else
    echo "User $USER does not exist – nothing to do."
fi
chsh "$(which zsh)" $USER

# nix
[[ ! -e .config/nix/nix.conf ]] && cp dotfiles/dot-config/nix/nix.conf .config/nix/nix.conf
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . /home/aamini.linux/.nix-profile/etc/profile.d/nix.sh
fi

# mise
export PATH="$PATH:$HOME/.local/bin"
curl https://mise.run | sh
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i --silent

