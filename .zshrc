# ── Environment ───────────────────────────────────────────────
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export EDITOR='nvim'
export VISUAL='nvim'
if [[ -z "$TERM" ]]; then
  export TERM=xterm-256color
fi
export OPENCODE_EXPERIMENTAL_OXFMT=1
export OLLAMA_HOST="http://127.0.0.1:11434"
# Global-only mise setting (kept out of .config/mise/config.toml so jj
# workspace copies of that file loaded as project configs don't warn).
export MISE_TRUSTED_CONFIG_PATHS="$HOME/.herdr/worktrees/:$HOME/.herdr/workspaces/"
# ── Path ──────────────────────────────────────────────────────
export PATH="$PATH:/usr/sbin:/sbin"
export PATH="$PATH:$HOME/.local/bin"
export PATH="$PATH:$HOME/.config/worktrunk/bin"
export PATH="$PATH:$HOME/.nix-profile/bin"
export PATH="$PATH:/opt/nvim-linux-x86_64/bin"
# ── Initialization ────────────────────────────────────────────
eval "$(mise activate zsh)"
if [ -e $HOME/.nix-profile/etc/profile.d/nix.sh ]; then . $HOME/.nix-profile/etc/profile.d/nix.sh; fi

# ── Aliases ───────────────────────────────────────────────────
alias lg='jjui'
alias ls='eza -1 --icons --group-directories-first'
alias k='kubectl'
alias copilot='copilot --yolo'
alias tree='erd'
alias rg="rg --hidden --glob '!.git'"
alias pr="gh-dash"
alias gd='hunk diff --watch'

gr() {
  cd "$(git rev-parse --show-toplevel 2>/dev/null)"
}

export DOJJO_WORKSPACE_PATH="$HOME/.herdr/workspaces/{{ repo }}/{{ name | sanitize }}"
eval "$(djo shell init zsh)"

# Print the primary jj workspace root: `jj root` points at the *current*
# workspace when run inside one. A workspace's .jj pointer (file, or
# .jj/repo) points at the primary's .jj dir instead — resolve that.
_jj_primary_root() {
  local root target base
  root=$(jj root 2>/dev/null) || return 1
  if [[ -f "$root/.jj" ]]; then
    target=$(<"$root/.jj")
    base="$root"
  elif [[ -f "$root/.jj/repo" ]]; then
    target=${$(<"$root/.jj/repo")%/repo}
    base="$root/.jj"
  else
    print -r -- "$root"
    return
  fi
  target=${target%/}
  [[ "$target" != /* ]] && target="$base/$target"
  print -r -- "${${target:A}:h}"
}

# Keep the old worktrunk muscle memory; goes through the djo() wrapper above
# so switch/remove still cd.
#
# `wt remove` reimplements the porcelain loop because removing the workspace
# you're standing in breaks djo twice: it crashes emitting the cd target (its
# cwd was deleted), and its backgrounded post-remove hook dies with it. So the
# wrapper verifies the removal itself, cd's home, and closes the matching
# herdr workspace synchronously.
wt() {
  if [[ "$1" == "remove" && -n "$HERDR_ENV" ]]; then
    local arg name="" primary output line ret
    primary=$(_jj_primary_root) || { print -u2 "wt: not in a jj repo"; return 1; }
    for arg in "${@:2}"; do
      [[ "$arg" != -* ]] && { name="$arg"; break; }
    done
    [[ -z "$name" ]] && name=$(command djo list --json 2>/dev/null | jq -r '.[] | select(.current) | .name')

    output="$(command djo --porcelain "$@")"
    ret=$?
    if (( ret != 0 )); then
      if (builtin cd "$primary" && command djo list --json | jq -e --arg n "$name" '.[] | select(.name == $n)' >/dev/null); then
        print -r -- "$output"
        return $ret
      fi
    fi
    while IFS= read -r line; do
      case "$line" in
        cd:*) builtin cd -- "${line#cd:}" ;;
        *) print -r -- "$line" ;;
      esac
    done <<< "$output"
    [[ ! -d $PWD ]] && builtin cd -- "$primary"
    [[ -z "$name" || "$name" == "default" ]] && return 0
    herdr-ws-close --repo "${primary:t}" --name "$name" ||
      print -u2 "wt: failed to close herdr workspace for '$name'"
    return 0
  fi
  djo "$@"
}

nvim()
{
    local nvim_new_dir_file="${XDG_CACHE_HOME:-$HOME/.cache}/nvim/newdir"
    mkdir -p "$(dirname "$nvim_new_dir_file")"
    rm -f "$nvim_new_dir_file"

    NVIM_NEW_DIR_FILE="$nvim_new_dir_file" command nvim "$@"

    if [ -f "$nvim_new_dir_file" ]; then
            local nvim_new_dir="$(cat "$nvim_new_dir_file")"
            rm -f "$nvim_new_dir_file" > /dev/null

            if [ -n "$nvim_new_dir" ] && [ -d "$nvim_new_dir" ]; then
                    cd "$nvim_new_dir"
            fi
    fi
}

vim()
{
    nvim "$@"
}

function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
	command yazi "$@" --cwd-file="$tmp"
	IFS= read -r -d '' cwd < "$tmp"
	[ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
	rm -f -- "$tmp"
}

# ── Platform: macOS ────────────────────────────────────────────
#
# Lima host setup notes:
#
# Delete existing default instance:
#   limactl stop default
#   limactl remove default
#
# Create and start a Docker-template default instance:
#   limactl create --name default template:docker -y
#   limactl start --mount-none
#
# Reconnect manually:
#   ssh -F ~/.lima/default/ssh.config lima-default
#
# Resize the default instance:
#   limactl edit default --memory 12
#   limactl edit default --cpus 8
#   limactl edit default --disk 100
#
# Recreate with preferred resources:
#   limactl stop default && limactl remove default && limactl create --mount-none --cpus=4 --disk=100 --memory=12 default -y && limactl start && lima
#
if [[ "$(uname -s)" == "Darwin" ]]; then
  export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin/"

  # Keep Lima reconnects as plain SSH instead of going through `limactl shell`.
  lima() {
    local instance="${LIMA_INSTANCE:-default}"
    ssh -F "$HOME/.lima/$instance/ssh.config" "lima-$instance" "$@"
  }

fi

# ── Platform: Lima Guest ───────────────────────────────────────
if [[ "$(uname -s)" == "Linux" ]] && getent hosts host.lima.internal >/dev/null 2>&1; then
  export OLLAMA_HOST="http://host.lima.internal:11434"

  # Make sure iptables and mount.fuse3 are available.
  export PATH="$PATH:/usr/sbin:/sbin"

fi

# Lima BEGIN
# Make sure iptables and mount.fuse3 are available
PATH="$PATH:/usr/sbin:/sbin"
export PATH
# Lima END

dev() {
  local -a targets=(wsl devbox none)
  [[ "$(uname -s)" == "Darwin" ]] && targets=(lima "${targets[@]}")
  local target=$(printf '%s\n' "${targets[@]}" | fzf --prompt='devbox target: ')
  case "$target" in
    lima) herdr --remote lima-default --remote-keybindings server ;;
    wsl|devbox) herdr --remote "$target" --remote-keybindings server ;;
  esac
}

# ── Completion ────────────────────────────────────────────────
autoload -Uz compinit
compinit
eval "$(djo shell completion zsh)"

# ── FZF ───────────────────────────────────────────────────────
source <(fzf --zsh)
export FZF_DEFAULT_COMMAND='fd --hidden'
export FZF_COMPLETION_OPTS="--preview '~/.config/fzf/fzf-preview.sh {}' --border --info=inline"

_fzf_compgen_path() {
  fd --hidden --follow --color=never . "$1"
}

_fzf_compgen_dir() {
  fd --hidden --follow --type directory --color=never . "$1"
}

source ~/.config/fzf/fzf-tab/fzf-tab.plugin.zsh

# ── Zoxide ────────────────────────────────────────────────────
eval "$(zoxide init zsh)"

# ── Theme ─────────────────────────────────────────────────────
eval "$(oh-my-posh init zsh --config ~/.config/oh-my-posh/themes/theme.toml)"


# ── Vim mode ──────────────────────────────────────────────────
bindkey -v
export KEYTIMEOUT=1

# Change cursor shape for different vi modes.
function zle-keymap-select {
  if [[ ${KEYMAP} == vicmd ]] ||
     [[ $1 = 'block' ]]; then
    echo -ne '\e[1 q'
  elif [[ ${KEYMAP} == main ]] ||
       [[ ${KEYMAP} == viins ]] ||
       [[ ${KEYMAP} = '' ]] ||
       [[ $1 = 'beam' ]]; then
    echo -ne '\e[5 q'
  fi
}
zle -N zle-keymap-select
zle-line-init() {
    zle -K viins # initiate `vi insert` as keymap (can be removed if `bindkey -V` has been set elsewhere)
    echo -ne "\e[5 q"
}
zle -N zle-line-init
echo -ne '\e[5 q' # Use beam shape cursor on startup.
preexec() { echo -ne '\e[5 q' ;} # Use beam shape cursor for each new prompt.

# ── herdr cd guard ────────────────────────────────────────────
# Block cd outside the herdr workspace root. Root defaults to the pane's
# launch cwd; overrides live in the aamini.cd-guard plugin config dir.
if [[ -n "$HERDR_ENV" ]]; then
  export HERDR_GUARD_ROOT="$PWD"
  typeset -g HERDR_GUARD_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/herdr/plugins/config/aamini.cd-guard"
  typeset -g HERDR_GUARD_SNAPPING=0

  _herdr_guard_root() {
    if [[ -n "$HERDR_WORKSPACE_ID" && -f "$HERDR_GUARD_CONFIG_DIR/roots" ]]; then
      local override
      override=$(awk -F'\t' -v id="$HERDR_WORKSPACE_ID" '$1 == id {print $2; exit}' "$HERDR_GUARD_CONFIG_DIR/roots")
      if [[ -n "$override" ]]; then
        print -r -- "$override"
        return
      fi
    fi
    print -r -- "$HERDR_GUARD_ROOT"
  }

  _herdr_guard_managed() {
    [[ -n "$HERDR_WORKSPACE_ID" && -f "$HERDR_GUARD_CONFIG_DIR/roots" ]] || return 1
    cut -f1 "$HERDR_GUARD_CONFIG_DIR/roots" | grep -qxF "$HERDR_WORKSPACE_ID"
  }

  _herdr_guard_disabled() {
    [[ "$HERDR_GUARD_DISABLED" == "1" ]] && return 0
    [[ -n "$HERDR_WORKSPACE_ID" && -f "$HERDR_GUARD_CONFIG_DIR/disabled" ]] || return 1
    grep -qxF "$HERDR_WORKSPACE_ID" "$HERDR_GUARD_CONFIG_DIR/disabled" 2>/dev/null
  }

  _herdr_guard_allowed() {
    local dir="$1" root="$2"
    [[ "$dir" == "$root" || "$dir" == "$root/"* ]] && return 0
    local rdir="${dir:A}" rroot="${root:A}"
    [[ "$rdir" == "$rroot" || "$rdir" == "$rroot/"* ]]
  }

  _herdr_guard_notify() {
    [[ -f "$HERDR_GUARD_CONFIG_DIR/config.toml" ]] || return 0
    grep -Eq '^[[:space:]]*notify[[:space:]]*=[[:space:]]*true' "$HERDR_GUARD_CONFIG_DIR/config.toml" || return 0
    command herdr notification show "cd guard" --body "$1" >/dev/null 2>&1 &!
  }

  _herdr_guard_chpwd() {
    (( HERDR_GUARD_SNAPPING )) && return 0
    _herdr_guard_managed || return 0
    _herdr_guard_disabled && return 0
    local root="$(_herdr_guard_root)"
    _herdr_guard_allowed "$PWD" "$root" && return 0
    print -u2 -- "cd blocked: $PWD is outside workspace root $root (use cd! to override)"
    _herdr_guard_notify "$PWD is outside workspace root $root"
    HERDR_GUARD_SNAPPING=1
    if [[ -n "$OLDPWD" ]] && _herdr_guard_allowed "$OLDPWD" "$root"; then
      builtin cd -- "$OLDPWD"
    else
      builtin cd -- "$root"
    fi
    HERDR_GUARD_SNAPPING=0
  }

  autoload -Uz add-zsh-hook
  add-zsh-hook chpwd _herdr_guard_chpwd

  'cd!'() {
    local ret
    HERDR_GUARD_SNAPPING=1
    builtin cd -- "$@"
    ret=$?
    HERDR_GUARD_SNAPPING=0
    return "$ret"
  }

  guard() {
    case "${1:-status}" in
      off)
        HERDR_GUARD_DISABLED=1
        print -- "cd guard: off (this shell)"
        ;;
      on)
        if ! _herdr_guard_managed; then
          print -- "cd guard: only active in wt workspaces"
          return 1
        fi
        unset HERDR_GUARD_DISABLED
        print -- "cd guard: on"
        ;;
      status)
        if ! _herdr_guard_managed; then
          print -- "cd guard: unmanaged (open via wt switch to enable)"
        elif _herdr_guard_disabled; then
          print -- "cd guard: disabled (root: $(_herdr_guard_root))"
        else
          print -- "cd guard: enabled (root: $(_herdr_guard_root))"
        fi
        ;;
      *)
        print -u2 -- "usage: guard [on|off|status]"
        return 2
        ;;
    esac
  }
fi
