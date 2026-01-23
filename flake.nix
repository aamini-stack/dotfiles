{
  description = "Dotfiles development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      # Define tools once, reuse in both outputs
      tools = pkgs: with pkgs; [
        stow
        zsh
        mise
        starship
        oh-my-posh
        neovim
        zellij
        wezterm
        lazygit
        delta
        yazi
        fzf
        bat
      ];
    in
    {
      # For global installation: nix profile install .#default
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.buildEnv {
            name = "dotfiles-tools";
            paths = tools pkgs;
          };
        });

      # For temporary shell: nix develop
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            buildInputs = tools pkgs;
          };
        });
    };
}
