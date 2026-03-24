#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
USER_NAME="${USER:-$(id -un)}"

log() {
  printf '==> %s\n' "$*"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_with_privileges() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    "$@"
  elif command_exists sudo; then
    sudo "$@"
  else
    "$@"
  fi
}

ensure_nix() {
  local nix_sh="$HOME/.nix-profile/etc/profile.d/nix.sh"

  if [[ -f "$nix_sh" ]]; then
    # shellcheck disable=SC1090
    . "$nix_sh"
  fi

  export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"

  if ! command_exists nix; then
    if ! command_exists curl; then
      log "curl is required to install Nix"
      return 1
    fi

    log "Installing Nix"
    sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon

    if [[ -f "$nix_sh" ]]; then
      # shellcheck disable=SC1090
      . "$nix_sh"
    fi

    export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"
  fi

  if ! command_exists nix; then
    log "Nix is installed but not available in this shell yet"
    log "Run: . \"$nix_sh\""
    return 1
  fi
}

install_profile() {
  log "Installing dotfiles toolchain"
  nix profile add "$REPO_ROOT#default" \
    --extra-experimental-features nix-command \
    --extra-experimental-features flakes
  hash -r
}

change_default_shell() {
  local zsh_path current_shell shell_listed status os_name

  zsh_path="$(command -v zsh || true)"
  if [[ -z "$zsh_path" ]]; then
    log "Skipping default shell change because zsh is not available yet"
    return
  fi

  current_shell="${SHELL:-}"
  if [[ "$current_shell" == "$zsh_path" ]]; then
    log "Default shell is already zsh"
    return
  fi

  os_name="$(uname -s)"
  if [[ "$os_name" == "Linux" ]]; then
    shell_listed="false"
    if [[ -r /etc/shells ]] && grep -Fxq "$zsh_path" /etc/shells; then
      shell_listed="true"
    fi

    if [[ "$shell_listed" != "true" ]]; then
      log "Adding zsh to /etc/shells"
      printf '%s\n' "$zsh_path" | run_with_privileges tee -a /etc/shells >/dev/null
    fi

    if command_exists passwd; then
      status="$(passwd --status "$USER_NAME" 2>/dev/null | awk '{print $2}' || true)"
      if [[ "$status" == "L" ]]; then
        log "Your account needs a password before the shell can be changed"
        run_with_privileges passwd "$USER_NAME"
      fi
    fi
  fi

  log "Changing default shell to zsh"
  run_with_privileges chsh -s "$zsh_path" "$USER_NAME"
}

main() {
  ensure_nix
  install_profile
  bash "$SCRIPT_DIR/stow.sh"
  change_default_shell
}

main "$@"
