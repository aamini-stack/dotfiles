# ── Environment ───────────────────────────────────────────────
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export EDITOR='nvim'
export VISUAL='nvim'
export TERM=xterm-256color
export OPENCODE_EXPERIMENTAL_OXFMT=1
export OLLAMA_HOST="http://host.lima.internal:11434"
# ── Path ──────────────────────────────────────────────────────
export PATH="$PATH:/usr/sbin:/sbin"
export PATH="$PATH:$HOME/.local/bin" # Used by lima vms
export PATH="$PATH:$HOME/.nix-profile/bin"
export PATH="$PATH:/opt/nvim-linux-x86_64/bin"
export PNPM_HOME="$XDG_DATA_HOME/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# ── Initialization ────────────────────────────────────────────
eval "$(mise activate zsh)"
if [ -e $HOME/.nix-profile/etc/profile.d/nix.sh ]; then . $HOME/.nix-profile/etc/profile.d/nix.sh; fi

# ── Aliases ───────────────────────────────────────────────────
alias ls='exa -1 --icons --group-directories-first'
alias vim='nvim'
alias lg='lazygit'
alias k='kubectl'
alias copilot='copilot --yolo'
alias tree='erd'
alias y='yazi'
alias rg="rg --hidden --glob '!.git'"

# VIM mode
bindkey -v

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
export FZF_DEFAULT_OPTS=""

export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_OPTS"
export FZF_CTRL_T_OPTS="$FZF_DEFAULT_OPTS"

export FZF_COMPLETION_OPTS="--preview '~/.fzf/fzf-preview.sh {}' --border --info=inline"
export FZF_COMPLETION_PATH_OPTS='--walker file,dir,follow,hidden'
export FZF_COMPLETION_DIR_OPTS="--walker dir,follow"

_fzf_compgen_path() {
  fd --hidden --follow --exclude .git . "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
}

_fzf_compgen_dir() {
  fd --type d --hidden --follow --exclude .git . "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
}

autoload -U compinit; compinit
source ~/.fzf/fzf-tab/fzf-tab.plugin.zsh

# ── Zoxide ────────────────────────────────────────────────────
eval "$(zoxide init zsh)"

# ── Theme ─────────────────────────────────────────────────────
eval "$(oh-my-posh init zsh --config ~/.config/oh-my-posh/themes/catppuccin.omp.json)"

# Lima BEGIN
# Make sure iptables and mount.fuse3 are available
PATH="$PATH:/usr/sbin:/sbin"
export PATH
# Lima END

