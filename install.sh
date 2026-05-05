#!/usr/bin/env bash
set -euo pipefail
cd $HOME

# clone: dotfiles
if [ ! -d "$HOME/dotfiles" ]; then
  git clone "https://github.com/aamini-stack/dotfiles.git" "$HOME/dotfiles"
fi

# wsl
# sudo cp dotfiles/misc/wsl.conf /etc/wsl.conf

# stow
sudo apt update -y
sudo apt install stow zsh -y
if [ -f "$HOME/.zshrc" ]; then
  rm "$HOME/.zshrc"
fi
cd dotfiles
stow --restow -v --target="$HOME" .
cd $HOME

# nix
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  . "$HOME/.nix-profile/etc/profile.d/nix.sh"
fi

# mise
export PATH="$PATH:$HOME/.local/bin"
echo "eval \"\$($HOME/.local/bin/mise activate bash)\"" >> ~/.bashrc
source .bashrc
curl https://mise.run | sh
mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i

# zsh
zsh_path="$(command -v zsh)"
sudo usermod -s "$zsh_path" "$USER"

# tpm (tmux plugin manager)
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  git clone "https://github.com/tmux-plugins/tpm.git" "$HOME/.tmux/plugins/tpm"
fi
