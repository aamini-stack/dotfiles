# Dotfiles

Bootstrap a fresh machine with:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/aamini-stack/dotfiles/main/scripts/install.sh)
```

This command:

- clones the repo into `~/dotfiles`
- installs `mise` with `apt`
- installs the toolchain with `mise i`
- stows the dotfiles into `$HOME`
- prompts before removing conflicting files
- switches your default shell to `zsh`

Notes:

- set `DOTFILES_DIR` if you want the repo cloned somewhere other than
  `~/dotfiles`
- if stow finds existing files, the installer shows the exact paths and asks
  before removing them
