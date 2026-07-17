#!/usr/bin/env bash
set -euo pipefail
cd "$HOME"

# clone: dotfiles
if [ ! -d "$HOME/dotfiles" ]; then
  git clone "https://github.com/aamini-stack/dotfiles.git" "$HOME/dotfiles"
fi

# stow
sudo apt update -y
sudo apt install stow zsh -y
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ -f "$HOME/.zshrc" ]; then
  rm "$HOME/.zshrc"
fi
cd dotfiles
stow --restow -v --target="$HOME" .
cd "$HOME"

# nix
if ! command -v nix &> /dev/null; then
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  # shellcheck source=/dev/null
  . "$HOME/.nix-profile/etc/profile.d/nix.sh"
fi

# mise
curl https://mise.run | sh
export PATH="$HOME/.local/bin:$PATH"
mise_activation="eval \"\$($HOME/.local/bin/mise activate bash)\""
grep -Fqx "$mise_activation" "$HOME/.bashrc" || printf '%s\n' "$mise_activation" >> "$HOME/.bashrc"
eval "$(mise activate bash)"
mise i
mise trust -y "$HOME/dotfiles/mise.toml"
mise -C "$HOME/dotfiles" install --monorepo
mise -C "$HOME/dotfiles" //:install

# zsh
zsh_path="$(command -v zsh)"
sudo usermod -s "$zsh_path" "$USER"
echo "Log out and back in for zsh to become the default shell."
