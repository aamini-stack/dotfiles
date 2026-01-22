{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "dotfiles-bootstrap";

  packages = with pkgs; [
    stow
    zsh
    mise
    starship
    neovim
    zellij
    wezterm
    lazygit
    delta
    yazi
  ];
}
