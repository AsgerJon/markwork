"""Sphinx configuration for markwork's own documentation, built by
markwork itself. This is the dogfood: enabling the extension renders the
markwork source verbatim, with every name a link to where it is defined.

The build does not import the documented package, does not introspect it,
and does not parse docstrings as markup. Each page is one source file,
highlighted by the engine and embedded through a raw-HTML directive, then
wired into a navigation tree. None of the autodoc machinery is loaded.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import os
from pathlib import Path

project = "markwork"
author = "Asger Jon Vistisen"
copyright = "2026, Asger Jon Vistisen"

#  The header version is read from pyproject.toml, the same file the build
#  takes its version from, so the docs always show the built version. Both
#  'release' and 'version' hold the full string.
_pyproject = Path(__file__).parent.parent / "pyproject.toml"
_handle = None
try:
  _handle = open(_pyproject, "r", encoding="utf-8")
except FileNotFoundError as exception:
  raise FileNotFoundError(str(_pyproject)) from exception
else:
  release = ""
  for _line in _handle:
    if _line.lstrip().startswith("version") and "=" in _line:
      release = _line.split("=", 1)[1].strip().strip("'\"")
      break
finally:
  try:
    _handle.close()
  except AttributeError:
    pass

version = release

#  The one line a user would write. markwork registers its config values,
#  runs the generator at builder-inited, and ships its own stylesheet.
extensions = ["markwork"]

exclude_patterns = ["_build"]

#  markwork is theme-independent, so the dogfood theme is just a
#  preference. It defaults to furo (in docs/requirements.txt) but honours
#  MARKWORK_THEME, so the docs can be previewed under any installed theme
#  without editing this file, for example MARKWORK_THEME=alabaster.
html_theme = os.environ.get("MARKWORK_THEME", "furo")
