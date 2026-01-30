sudo apt update
sudo apt install -y stow 
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
. ~/.nix-profile/etc/profile.d/nix.sh
cd ~
git clone https://github.com/aamini-stack/dotfiles
cd dotfiles
./install.sh
command -v zsh | sudo tee -a /etc/shells
chsh -s $(which zsh)
