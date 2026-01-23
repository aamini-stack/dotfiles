sudo dnf install -y git stow xz
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
. /home/aamini/.nix-profile/etc/profile.d/nix.sh
git clone https://github.com/aamini-stack/dotfiles
cd dotfiles
./install.sh
sudo chsh $USER -s $(which zsh)
