# ALIASES
alias g='lazygit'

source ~/scripts/fzf.sh
export FZF_CTRL_T_OPTS="--preview '~/scripts/fzf-preview.sh {}'"

eval "$(oh-my-posh init zsh --config ~/.config/oh-my-posh/themes/catppuccin.omp.json)"

export XDG_CONFIG_HOME="$HOME/.config"

eval "$(starship init zsh)"
export PATH="$PATH:/opt/nvim-linux-x86_64/bin"

autoload -Uz compinit
compinit

alias python=python3
alias vim='nvim'

export EDITOR='nvim'
export VISUAL='nvim'

export JAVA_HOME='/Users/aamini/Library/Java/JavaVirtualMachines/openjdk-17.0.1/Contents/Home'

# pnpm
export PNPM_HOME="/Users/aamini/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# Mise
eval "$(mise activate zsh)" # this sets up interactive sessions
export PATH="$HOME/.local/bin:$PATH"

