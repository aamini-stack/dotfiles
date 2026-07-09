# ── Environment ───────────────────────────────────────────────
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export EDITOR='nvim'
export VISUAL='nvim'
export TERM=xterm-256color
export OPENCODE_EXPERIMENTAL_OXFMT=1
if [[ "$(uname -s)" == "Linux" ]] && getent hosts host.lima.internal >/dev/null 2>&1; then
  export OLLAMA_HOST="http://host.lima.internal:11434"
else
  export OLLAMA_HOST="http://127.0.0.1:11434"
fi
# ── Path ──────────────────────────────────────────────────────
export PATH="$PATH:/usr/sbin:/sbin"
export PATH="$PATH:$HOME/.local/bin" # Used by lima vms
export PATH="$PATH:$HOME/.nix-profile/bin"
export PATH="$PATH:/opt/nvim-linux-x86_64/bin"
# ── Initialization ────────────────────────────────────────────
eval "$(mise activate zsh)"
if [ -e $HOME/.nix-profile/etc/profile.d/nix.sh ]; then . $HOME/.nix-profile/etc/profile.d/nix.sh; fi

# ── Aliases ───────────────────────────────────────────────────
alias ls='eza -1 --icons --group-directories-first'
alias k='kubectl'
alias copilot='copilot --yolo'
alias tree='erd'
alias rg="rg --hidden --glob '!.git'"
alias pr="gh-dash"

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

lg()
{
    local lazygit_new_dir_file="$HOME/.lazygit/newdir"
    local lazygit_start_root

    lazygit_start_root="$(git rev-parse --show-toplevel 2>/dev/null)"
    mkdir -p "$(dirname "$lazygit_new_dir_file")"
    rm -f "$lazygit_new_dir_file"
    export LAZYGIT_NEW_DIR_FILE="$lazygit_new_dir_file"

    lazygit "$@"

    if [ -f "$lazygit_new_dir_file" ]; then
            local lazygit_new_dir="$(cat "$lazygit_new_dir_file")"
            rm -f "$lazygit_new_dir_file" > /dev/null

            if [ -n "$lazygit_new_dir" ] && [ -d "$lazygit_new_dir" ] && [ "$lazygit_new_dir" != "$lazygit_start_root" ]; then
                    cd "$lazygit_new_dir"
            fi
    fi
}

# Keep Lima reconnects as plain SSH instead of going through `limactl shell`.
lima() {
  local instance="${LIMA_INSTANCE:-default}"
  ssh -F "$HOME/.lima/$instance/ssh.config" "lima-$instance" "$@"
}

function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
	command yazi "$@" --cwd-file="$tmp"
	IFS= read -r -d '' cwd < "$tmp"
	[ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
	rm -f -- "$tmp"
}

# Auto-connect new interactive host shells to a Lima VM.
# REMOVE THE EXEC COMMAND TO ALLOW GOING BACK TO MAC HOST WHEN RUNNING 'exit'
auto_lima_ssh() {
  local instance="${LIMA_AUTO_SSH_INSTANCE:-default}"
  local ssh_config="$HOME/.lima/$instance/ssh.config"
  local hostagent_socket="$HOME/.lima/$instance/ha.sock"

  [[ -o interactive ]] || return 0
  [[ -n "${LIMA_AUTO_SSH_DISABLED:-}" ]] && return 0
  [[ -n "${SSH_CONNECTION:-}" || -n "${SSH_TTY:-}" ]] && return 0
  [[ "${SHLVL:-1}" -gt 1 ]] && return 0
  [[ -t 0 && -t 1 ]] || return 0

  [[ -f "$ssh_config" ]] || return 0
  [[ -S "$hostagent_socket" ]] || return 0
  ssh -F "$ssh_config" "lima-$instance"
}

auto_lima_ssh

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

# Lima BEGIN
# Make sure iptables and mount.fuse3 are available
PATH="$PATH:/usr/sbin:/sbin"
export PATH
# Lima END


if command -v wt >/dev/null 2>&1; then eval "$(command wt config shell init zsh)"; fi

# start in tmux: https://unix.stackexchange.com/questions/43601/how-can-i-set-my-default-shell-to-start-up-tmux
# if command -v tmux &> /dev/null && [ -n "$PS1" ] && [[ ! "$TERM" =~ screen ]] && [[ ! "$TERM" =~ tmux ]] && [ -z "$TMUX" ]; then
#  exec tmux
# fi

export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin/"


# Vite+ bin (https://viteplus.dev)
. "$HOME/.vite-plus/env"
