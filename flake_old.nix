{
  description = "Dotfiles bootstrap environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-darwin" "aarch64-darwin" "x86_64-linux" "aarch64-linux" ];

      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            name = "dotfiles-bootstrap";
            packages = with pkgs; [
              stow
              zsh
              mise
              starship
              neovim
              zellij
              (if pkgs.stdenv.isLinux then wezterm else null)
              lazygit
              delta
              yazi
            ] ++ lib.optionals pkgs.stdenv.isLinux [
              # Fedora-specific: wezterm not in nixpkgs, install via alternative
              # or use wezterm-nightly from nixpkgs
              wezterm
            ];

            shellHook = ''
              echo "Dotfiles bootstrap shell ready. Run 'exit' to return."
              echo "Install permanently with: nix profile install .#default --profile $HOME/.nix-profile"
            '';
          };
        }
      );

      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.symlinkJoin {
            name = "dotfiles-packages";
            paths = with pkgs; [
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
          };
        }
      );
    };
}
