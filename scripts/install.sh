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
  git clone https://github.com/tmux-plugins/tpm.git ~/.tmux/plugins/tpm
fi

curl https://mise.run | sh
sudo apt install stow -y
cd dotfiles
stow --restow -v --target="$HOME" .
cd $HOME

export PATH="$PATH:~/.local/bin"
echo 'export PATH="$PATH:~/.local/bin"' >> ~/.bashrc
echo "eval \"\$(/home/aamini.linux/.local/bin/mise activate bash)\"" >> ~/.bashrc

mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i

# zsh
command -v zsh | sudo tee -a /etc/shells
sudo chsh -s "$(which zsh)" $USER

