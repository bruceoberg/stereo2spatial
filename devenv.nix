{ pkgs, ... }:

{
  packages = [
    pkgs.just
  ];

  languages.python = {
    enable = true;
    package = pkgs.python312;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  enterShell = ''
    if [ ! -x /usr/bin/swiftc ]; then
      echo ""
      echo "⚠️  swiftc not found. Install Xcode Command Line Tools:"
      echo "    xcode-select --install"
      echo ""
    fi
  '';
}
