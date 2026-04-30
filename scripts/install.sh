#!/usr/bin/env bash
set -euo pipefail
cd $HOME

# nix
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . $HOME/.nix-profile/etc/profile.d/nix.sh
fi

# tmux plugin manager (tpm)
if [ ! -d "$HOME/.config/tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm.git ~/tmux/plugins/tpm
fi

# mise
mkdir -p .config/mise
cp -n $HOME/dotfiles/.config/mise/config.toml $HOME/.config/mise/config.toml
mkdir -p .config/nix
cp -n $HOME/dotfiles/.config/nix/nix.conf $HOME/.config/nix/nix.conf
export PATH="$PATH:$HOME/.local/bin"
curl https://mise.run | sh
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i
eval "$(mise activate bash)"
rm -r $HOME/.config/nix
rm -r $HOME/.config/mise
if [ -d "$HOME/.zshrc" ]; then
  rm "$HOME/.zshrc"
fi
cd dotfiles
mise trust
stow --restow -v --target="$HOME" .
sudo chsh -s "$(which zsh)" $USER

