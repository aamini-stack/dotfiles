#!/usr/bin/env bash
# Runs inside the container as the unprivileged `test` user.
set -euo pipefail

# install.sh clones from GitHub only when ~/dotfiles is absent, so seeding a
# copy of the mounted repo makes it exercise the local checkout instead.
# Root copy: some repo files (jj metadata) are unreadable to other uids.
sudo cp -a /opt/dotfiles-src "$HOME/dotfiles"
sudo chown -R test:test "$HOME/dotfiles"

"$HOME/dotfiles/install.sh" < /dev/null

zsh -ic '
  missing=0
  for cmd in mise node uv az oh-my-posh stow fzf zoxide; do
    if ! command -v "$cmd" > /dev/null; then
      echo "MISSING: $cmd"
      missing=1
    fi
  done
  [ -L "$HOME/.zshrc" ] || { echo "MISSING: ~/.zshrc symlink"; missing=1; }
  exit "$missing"
'

echo "E2E PASS"
