# Dependencies
- stow
- zsh
- mise
- starship
- neovim

```
curl -sS https://starship.rs/install.sh | sh

sudo dnf copr enable lihaohong/yazi
sudo dnf install yazi

sudo dnf install zsh
sudo chsh $USER -s $(which zsh)

sudo dnf copr enable jdxcode/mise
sudo dnf install mise

sudo dnf install -y neovim python3-neovim
```