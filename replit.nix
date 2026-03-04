{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.nodejs-18_x
    pkgs.postgresql_15
    pkgs.redis
    pkgs.git
  ];
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.libpq
    ];
  };
}
