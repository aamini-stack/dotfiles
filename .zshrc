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
export PATH="$PATH:$HOME/.nix-profile/bin"
export PATH="$PATH:/opt/nvim-linux-x86_64/bin"

# ── Initialization ────────────────────────────────────────────
eval "$(mise activate zsh)"
if [ -e $HOME/.nix-profile/etc/profile.d/nix.sh ]; then . $HOME/.nix-profile/etc/profile.d/nix.sh; fi

# ── Aliases ───────────────────────────────────────────────────
alias lg='jjui'
alias ls='eza -1 --icons --group-directories-first'
alias k='kubectl'
alias tree='erd'
alias pr="gh-dash"
alias gd='hunk diff --watch'

jjui() {
  local result_file destination exit_code
  result_file="$(mktemp "${TMPDIR:-/tmp}/jjui-workspace.XXXXXX")" || return

  JJUI_WORKSPACE_RESULT_FILE="$result_file" command jjui "$@"
  exit_code=$?
  destination="$(<"$result_file")"
  command rm -f -- "$result_file"

  if [[ -n "$destination" && -d "$destination" ]]; then
    builtin cd -- "$destination" || return
  fi
  return "$exit_code"
}

wt() {
  if [[ "$1" == "switch" ]]; then
    local output exit_code destination result_file
    result_file="$(mktemp "${TMPDIR:-/tmp}/wt-result.XXXXXX")" || return
    output="$(WT_RESULT_FILE="$result_file" command wt "$@")"
    exit_code=$?
    [[ -n "$output" ]] && print -r -- "$output"
    destination="$(<"$result_file")"
    command rm -f -- "$result_file"
    if [[ -n "$destination" ]]; then
      print -r -- "$destination"
      builtin cd -- "$destination"
    fi
    return "$exit_code"
  fi
  command wt "$@"
}

gr() {
  local root
  root=$(git rev-parse --show-toplevel 2>/dev/null) || root=$(jj root 2>/dev/null) || return 1
  cd "$root"
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
PATH="$PATH:/usr/sbin:/sbin" # Make sure iptables and mount.fuse3 are available
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
