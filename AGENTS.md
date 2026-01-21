# AGENTS.md

This is a personal dotfiles repository containing terminal and editor configurations for macOS/Linux systems.

## Repository Structure

- `.config/` - XDG config directory containing:
  - `nvim/` - Neovim configuration (based on kickstart.nvim)
  - `zellij/` - Zellij terminal multiplexer config and layouts
  - `starship.toml` - Starship prompt configuration
  - `.wezterm.lua` - WezTerm terminal emulator configuration
- `.zshrc` - Zsh shell configuration
- `.zprofile` - Zsh profile (environment variables)
- `.gitconfig` - Git configuration
- `.stowrc` - GNU Stow configuration

## Installation

This repo uses [GNU Stow](https://www.gnu.org/software/stow/) to symlink dotfiles to the home directory. The `.stowrc` file configures stow to target `~` and handle dotfiles.

To install, clone the repo and run `stow .` from the repo root.

## Dependencies

- stow
- zsh
- mise (runtime version manager)
- starship (prompt)
- neovim

## Conventions

- All configs follow XDG base directory specification where supported
- Neovim uses Lua-based configuration with lazy.nvim for plugin management
- Shell configs are minimal and delegate to tools like starship and mise
