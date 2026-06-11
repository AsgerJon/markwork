"""
The 'detectPackage' function resolves the package directory to document.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path


def detectPackage(srcRoot: Path, name) -> Path:
  """Resolve the package directory under the source root.

  A configured name wins; otherwise the source root must hold exactly one
  importable package and that one is used. Anything else is ambiguous and
  raises, so a misconfigured project fails loudly rather than documenting
  the wrong tree.

  Parameters
  ----------
  srcRoot : Path
      The source root to search.
  name : str or None
      The configured package name, or None to auto-detect.

  Returns
  -------
  Path
      The resolved package directory.

  Raises
  ------
  RuntimeError
      When no name is configured and the source root does not hold
      exactly one importable package.
  """
  if name is not None:
    return srcRoot / name
  candidates = sorted(
      child for child in srcRoot.iterdir()
      if child.is_dir() and (child / "__init__.py").exists()
  )
  if len(candidates) == 1:
    return candidates[0]
  info = ("markwork could not pick a package under %s: set "
          "markwork_package in conf.py. Found: %s")
  names = ", ".join(child.name for child in candidates) or "none"
  raise RuntimeError(info % (srcRoot, names))
