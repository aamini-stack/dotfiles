alias python=python3
alias vim='nvim'

cd Developer

export JAVA_HOME='/Users/aamini/Library/Java/JavaVirtualMachines/openjdk-17.0.1/Contents/Home'

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /usr/local/bin/terraform terraform

# pnpm
export PNPM_HOME="/Users/aamini/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# Mise
eval "$(mise activate zsh)" # this sets up interactive sessions
