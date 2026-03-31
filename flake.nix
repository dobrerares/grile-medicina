{
  description = "Grile Medicina OCR Pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
      in {
        devShells.default = pkgs.mkShell {
          packages = [
            (python.withPackages (ps: [
              ps.pymupdf
              ps.pip
            ]))
          ];

          shellHook = ''
            # Create venv for pip-only packages (mistralai, rapidfuzz)
            if [ ! -d .venv ]; then
              python -m venv .venv --system-site-packages
              .venv/bin/pip install mistralai rapidfuzz
            fi
            source .venv/bin/activate
          '';
        };
      });
}
