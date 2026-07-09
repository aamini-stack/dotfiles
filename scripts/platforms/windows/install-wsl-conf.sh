#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_conf="$script_dir/wsl.conf"
target_conf="/etc/wsl.conf"

if [[ ! -f "$source_conf" ]]; then
  printf 'Missing source config: %s\n' "$source_conf" >&2
  exit 1
fi

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  install -m 0644 "$source_conf" "$target_conf"
else
  sudo install -m 0644 "$source_conf" "$target_conf"
fi

printf 'Installed %s to %s\n' "$source_conf" "$target_conf"
printf 'Restart WSL from Windows for changes to apply: wsl.exe --shutdown\n'
