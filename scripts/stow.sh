#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

log() {
  printf '==> %s\n' "$*"
}

run_stow() {
  local output_file="$1"

  if (
    cd "$REPO_ROOT"
    LC_ALL=C stow --restow -v --target="$HOME" --dotfiles .
  ) >"$output_file" 2>&1; then
    cat "$output_file"
    return 0
  fi

  cat "$output_file"
  return 1
}

collect_conflicts() {
  local output_file="$1"
  local line relative_path

  while IFS= read -r line; do
    case "$line" in
      *"existing target is neither a link nor a directory: "*|*"existing target is not owned by stow: "*)
        relative_path="${line##*: }"
        ;;
      *)
        continue
        ;;
    esac

    if [[ -n "$relative_path" ]]; then
      printf '%s\n' "$HOME/$relative_path"
    fi
  done < "$output_file" | sort -u
}

remove_conflicts() {
  local conflict

  log "Removing conflicting files"

  for conflict in "$@"; do
    if [[ ! -e "$conflict" && ! -L "$conflict" ]]; then
      continue
    fi

    rm -rf "$conflict"
  done

  log "Conflicting files removed"
}

should_override_conflicts() {
  local conflict

  if [[ ! -t 0 ]]; then
    return 1
  fi

  printf 'Stow found these conflicting paths:\n'
  for conflict in "$@"; do
    printf '  - %s\n' "$conflict"
  done

  printf 'Remove them and retry? [y/N] '
  read -r reply
  [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

main() {
  local conflicts=()
  local conflict
  local output_file

  output_file="$(mktemp)"
  trap 'rm -f "$output_file"' EXIT

  if run_stow "$output_file"; then
    return 0
  fi

  while IFS= read -r conflict; do
    [[ -n "$conflict" ]] && conflicts+=("$conflict")
  done < <(collect_conflicts "$output_file")

  if [[ ${#conflicts[@]} -eq 0 ]]; then
    log "Stow failed, but the conflicting paths could not be determined automatically"
    return 1
  fi

  if ! should_override_conflicts "${conflicts[@]}"; then
    log "Stow stopped because of conflicts"
    return 1
  fi

  if ! remove_conflicts "${conflicts[@]}"; then
    log "Unable to remove conflicting files"
    return 1
  fi

  log "Retrying stow after removing conflicts"
  run_stow "$output_file"
}

main "$@"
