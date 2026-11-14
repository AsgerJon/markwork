"""
Run markwork as a module: 'python -m markwork <repo>' is the same
ephemeral build as the 'markwork' console script.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from ._cli import main

if __name__ == "__main__":
  raise SystemExit(main())
