#!/usr/bin/env bash
set -euo pipefail
cd $HOME

# nix
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . $HOME/.nix-profile/etc/profile.d/nix.sh
fi

# mise
mkdir -p .config/mise
cp $HOME/dotfiles/.config/mise/config.toml $HOME/.config/mise/config.toml
mkdir -p .config/nix
cp $HOME/dotfiles/.config/nix/nix.conf $HOME/.config/nix/nix.conf
export PATH="$PATH:$HOME/.local/bin"
curl https://mise.run | sh
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i
eval "$(mise activate bash)"
rm -r $HOME/.config/nix 
rm -r $HOME/.config/mise
rm .zshrc
stow --restow -v --target="$HOME" .
sudo chsh -s "$(which zsh)" $USER

# tmux plugin manager (tpm)
if [ ! -d "$HOME/.config/tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm.git ~/.config/tmux/plugins/tpm
fi

# curl -fsSL https://get.docker.com -o get-docker.sh
# sudo sh ./get-docker.sh
# sudo usermod -aG docker $USER
# sudo reboot

