#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/aamini-stack/dotfiles.git"
INSTALL_DIR="${DOTFILES_DIR:-$HOME/dotfiles}"

log() {
  printf '==> %s\n' "$*"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

resolve_login_shell() {
  local user_name login_shell

  user_name="${USER:-$(id -un)}"

  if command_exists getent; then
    login_shell="$(getent passwd "$user_name" | cut -d: -f7)"
  elif command_exists dscl; then
    login_shell="$(dscl . -read "/Users/$user_name" UserShell 2>/dev/null | awk '{print $2}')"
  else
    login_shell="${SHELL:-}"
  fi

  printf '%s\n' "$login_shell"
}

maybe_start_login_shell() {
  local current_shell login_shell

  if [[ ! -t 0 || ! -t 1 ]]; then
    return
  fi

  login_shell="$(resolve_login_shell)"
  current_shell="${SHELL:-}"

  if [[ -z "$login_shell" || ! -x "$login_shell" || "$login_shell" == "$current_shell" ]]; then
    return
  fi

  case "${DOTFILES_AUTO_LOGIN_SHELL:-1}" in
    0|false|FALSE|no|NO)
      log "Default shell is now $login_shell"
      log "Start it without reconnecting: exec \"$login_shell\" -l"
      return
      ;;
  esac

  log "Default shell is now $login_shell"
  log "Starting a login shell now. Exit once to return to your previous shell."
  export SHELL="$login_shell"
  exec "$login_shell" -l
}

main() {
  if ! command_exists git; then
    log "git is required to bootstrap dotfiles"
    exit 1
  fi

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "Updating existing dotfiles repo in $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
  elif [[ -e "$INSTALL_DIR" ]]; then
    log "$INSTALL_DIR exists but is not a git repo"
    exit 1
  else
    log "Cloning dotfiles repo into $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
  fi

  bash "$INSTALL_DIR/scripts/install.sh"
  maybe_start_login_shell
}

main "$@"
