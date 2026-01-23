# Source Nix profile first so nix-installed tools are available
if [ -e /home/aamini/.nix-profile/etc/profile.d/nix.sh ]; then . /home/aamini/.nix-profile/etc/profile.d/nix.sh; fi

eval "$(mise activate zsh --shims)" # this sets up non-interactive sessions
