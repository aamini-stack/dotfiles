sudo apt update
sudo apt install -y stow 
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon
. ~/.nix-profile/etc/profile.d/nix.sh
cd ~
git clone https://github.com/aamini-stack/dotfiles
cd dotfiles
./install.sh
sudo command -v zsh | sudo tee -a /etc/shells
sudo chsh -s $(which zsh)
