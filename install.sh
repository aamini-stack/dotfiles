#!/usr/bin/env bash
set -euo pipefail
cd "$HOME"

# bootstrap: gum
GUM_VERSION="0.16.2"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v gum &> /dev/null; then
  mkdir -p "$HOME/.local/bin"
  arch="$(uname -m)"
  case "$arch" in
    x86_64) gum_arch="x86_64" ;;
    aarch64) gum_arch="arm64" ;;
    *) echo "Unsupported arch: $arch" >&2; exit 1 ;;
  esac
  curl -fsSL "https://github.com/charmbracelet/gum/releases/download/v${GUM_VERSION}/gum_${GUM_VERSION}_Linux_${gum_arch}.tar.gz" \
    | tar -xz -C /tmp "gum_${GUM_VERSION}_Linux_${gum_arch}/gum"
  mv "/tmp/gum_${GUM_VERSION}_Linux_${gum_arch}/gum" "$HOME/.local/bin/gum"
fi

gum style \
  --border double --border-foreground 212 --padding "1 3" --margin "1 0" \
  --align center --width 44 \
  "$(gum style --bold --foreground 212 'dotfiles')" \
  "github.com/aria-amini/dotfiles"

step() {
  gum style --margin "1 0 0 0" --bold --foreground 99 "▸ $1"
}

# clone: dotfiles
step "Dotfiles"
if [ ! -d "$HOME/dotfiles" ]; then
  gum spin --title "Cloning dotfiles..." -- \
    git clone "https://github.com/aria-amini/dotfiles.git" "$HOME/dotfiles"
else
  gum style --foreground 245 "  already cloned"
fi

# git (latest stable from ppa, jj requires >= 2.41)
step "Git"
gum spin --title "Installing git from ppa..." -- bash -c '
  sudo add-apt-repository -y ppa:git-core/ppa
  sudo apt update -y
  sudo apt install git -y
'

# stow
step "Stow"
gum spin --title "Installing stow and zsh..." -- \
  sudo apt install stow zsh -y
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ -f "$HOME/.zshrc" ]; then
  rm "$HOME/.zshrc"
fi
gum spin --title "Linking dotfiles..." -- bash -c "
  cd \"$HOME/dotfiles\"
  stow --restow --target=\"$HOME\" .
"

# nix
step "Nix"
if ! command -v nix &> /dev/null; then
  gum spin --title "Installing nix..." -- \
    sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
  # shellcheck source=/dev/null
  . "$HOME/.nix-profile/etc/profile.d/nix.sh"
else
  gum style --foreground 245 "  already installed"
fi

# mise
step "Mise"
gum spin --title "Installing mise..." -- \
  bash -c 'curl -fsSL https://mise.run | sh'
mise_activation="eval \"\$($HOME/.local/bin/mise activate bash)\""
grep -Fqx "$mise_activation" "$HOME/.bashrc" || printf '%s\n' "$mise_activation" >> "$HOME/.bashrc"
eval "$(mise activate bash)"
gum spin --title "Installing runtimes..." -- mise i
mise trust -y "$HOME/dotfiles/mise.toml"
gum spin --title "Installing dotfiles tools..." -- \
  mise -C "$HOME/dotfiles" install --monorepo
gum spin --title "Running tool install tasks..." -- \
  mise -C "$HOME/dotfiles" //:install

# zsh
step "Shell"
zsh_path="$(command -v zsh)"
gum spin --title "Setting zsh as default shell..." -- \
  sudo usermod -s "$zsh_path" "$USER"

gum style \
  --border rounded --border-foreground 82 --padding "0 3" --margin "1 0" \
  --foreground 82 "✓ Install complete"

gum confirm "Log out is required for zsh. Open a new shell now?" && exec zsh || true
