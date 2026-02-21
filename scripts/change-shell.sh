command -v zsh | sudo tee -a /etc/shells
chsh -s "$(which zsh)" "$USER"
