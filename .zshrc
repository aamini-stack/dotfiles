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
alias ls='eza -1 --icons --group-directories-first'
alias k='kubectl'
alias copilot='copilot --yolo'
alias tree='erd'
alias rg="rg --hidden --glob '!.git'"
alias pr="gh-dash"
alias setup="herdr-project-layout"

gr() {
  cd "$(git rev-parse --show-toplevel 2>/dev/null)"
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

function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
	command yazi "$@" --cwd-file="$tmp"
	IFS= read -r -d '' cwd < "$tmp"
	[ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
	rm -f -- "$tmp"
}

# ── Platform modules ───────────────────────────────────────────
source_if_exists() {
  [[ -r "$1" ]] && source "$1"
}

source_if_exists "$HOME/scripts/platforms/macos/host.zsh"
source_if_exists "$HOME/scripts/platforms/macos/lima.zsh"

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

# Vite+ bin (https://viteplus.dev)
. "$HOME/.vite-plus/env"
