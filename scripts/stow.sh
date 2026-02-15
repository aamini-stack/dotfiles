#!/usr/bin/env bash
set -euo pipefail

DIR="$(dirname "$(realpath "$0")")"
cd $DIR
cd ..

LC_ALL=C stow -v --target="$HOME" --dotfiles .

