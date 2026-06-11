"""
The 'absModule' function resolves an import target to an absolute dotted
module.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path


def absModule(srcRoot: Path, pyfile: Path, level: int, module) -> str:
  """Resolve an import target to an absolute dotted module.

  Relative imports (level >= 1) are resolved against the file's package. A
  relative import in a file outside the source root (for example a test)
  cannot name a project symbol, so it resolves to the empty string.

  Parameters
  ----------
  srcRoot : Path
      The source root the package lives under.
  pyfile : Path
      The file containing the import.
  level : int
      The import's relative level: 0 for an absolute import.
  module : str or None
      The dotted module named by the import, if any.

  Returns
  -------
  str
      The absolute dotted module, or the empty string when it cannot be
      resolved.
  """
  if level == 0:
    return module or ""
  try:
    pkgParts = pyfile.parent.relative_to(srcRoot).parts
  except ValueError:
    return ""
  base = list(pkgParts[:len(pkgParts) - (level - 1)])
  if module:
    base += module.split(".")
  return ".".join(base)
