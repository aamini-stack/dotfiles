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
if command -v git &> /dev/null && grep -qs "git-core" /etc/apt/sources.list.d/*; then
  gum style --foreground 245 "  already installed ($(git --version))"
else
  gum spin --title "Installing git from ppa..." -- bash -c '
    sudo add-apt-repository -y ppa:git-core/ppa
    sudo apt install git -y
  '
fi

# stow
step "Stow"
if command -v stow &> /dev/null && command -v zsh &> /dev/null; then
  gum style --foreground 245 "  already installed"
else
  gum spin --title "Installing stow and zsh..." -- \
    sudo apt install stow zsh -y
fi
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
if command -v mise &> /dev/null; then
  gum style --foreground 245 "  already installed"
else
  gum spin --title "Installing mise..." -- \
    bash -c 'curl -fsSL https://mise.run | sh'
fi
mise_activation="eval \"\$($HOME/.local/bin/mise activate bash)\""
grep -Fqx "$mise_activation" "$HOME/.bashrc" || printf '%s\n' "$mise_activation" >> "$HOME/.bashrc"
eval "$(mise activate bash)"
gum spin --title "Installing runtimes..." -- mise i
gum spin --title "Trusting dotfiles config..." -- \
  mise trust -y "$HOME/dotfiles/mise.toml"
gum spin --title "Installing dotfiles tools..." -- \
  mise -C "$HOME/dotfiles" install --monorepo
gum spin --title "Running tool install tasks..." -- \
  mise -C "$HOME/dotfiles" //:install

# tailscale (system daemon; falls back to `mise run tailscaled` without systemd)
step "Tailscale"
if command -v systemctl &> /dev/null; then
  if ! dpkg -s tailscale &> /dev/null; then
    gum spin --title "Installing tailscale..." -- \
      bash -c 'curl -fsSL https://tailscale.com/install.sh | sh'
  else
    gum style --foreground 245 "  already installed"
  fi
  gum spin --title "Enabling tailscaled..." -- \
    sudo systemctl enable --now tailscaled
else
  gum style --foreground 245 "  no systemd, skipping (use: mise -C ~/dotfiles run tailscaled)"
fi

# zsh
step "Shell"
zsh_path="$(command -v zsh)"
shell_changed=false
if [ "$(getent passwd "$USER" | cut -d: -f7)" = "$zsh_path" ]; then
  gum style --foreground 245 "  already default"
else
  gum spin --title "Setting zsh as default shell..." -- \
    sudo usermod -s "$zsh_path" "$USER"
  shell_changed=true
fi

gum style \
  --border rounded --border-foreground 82 --padding "0 3" --margin "1 0" \
  --foreground 82 "✓ Install complete"

if command -v tailscale &> /dev/null && ! sudo tailscale status &> /dev/null; then
  gum style \
    --border rounded --border-foreground 214 --padding "0 3" --margin "1 0" \
    "$(gum style --bold --foreground 214 'One manual step:')" \
    "run: sudo tailscale up" \
    "then open the login link it prints"
fi

if [ "$shell_changed" = true ]; then
  gum confirm "Log out is required for zsh. Open a new shell now?" && exec zsh || true
fi
