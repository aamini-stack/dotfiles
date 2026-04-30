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

# mise
mkdir -p .config/mise
cp -u $HOME/dotfiles/.config/mise/config.toml $HOME/.config/mise/config.toml
mkdir -p .config/nix
cp -u $HOME/dotfiles/.config/nix/nix.conf $HOME/.config/nix/nix.conf

sudo add-apt-repository -y ppa:jdxcode/mise
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y mise
echo 'export PATH="$PATH:~/.local/bin"' >> ~/.bashrc
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
mise plugin list | grep -q "^nix" || mise plugin install nix https://github.com/jbadeau/mise-nix.git
mise i
rm -r $HOME/.config/nix
rm -r $HOME/.config/mise
cd dotfiles
mise trust
stow --restow -v --target="$HOME" .
command -v zsh | sudo tee -a /etc/shells
sudo chsh -s "$(which zsh)" $USER

