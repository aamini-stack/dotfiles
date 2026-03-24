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
}

main "$@"
