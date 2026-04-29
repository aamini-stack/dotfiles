#!/usr/bin/env bash
set -euo pipefail
cd $HOME

# stow
rm -f .zshrc
sudo apt update
sudo apt install stow -yq
stow -v --target $HOME --dir "$HOME/dotfiles" .

# zsh
sudo apt install zsh -yq
sudo chsh -s "$(which zsh)" $USER

# nix
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . $HOME/.nix-profile/etc/profile.d/nix.sh
fi

# tmux plugin manager (tpm)
if [ ! -d "$HOME/.config/tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm.git ~/.config/tmux/plugins/tpm
fi

# mise
export PATH="$PATH:$HOME/.local/bin"
curl https://mise.run | sh
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i

# curl -fsSL https://get.docker.com -o get-docker.sh
# sudo sh ./get-docker.sh
# sudo usermod -aG docker $USER
# sudo reboot
