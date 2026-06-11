"""
The 'parseInit' function reads a package __init__.py into its public
re-export mapping.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
from pathlib import Path


def parseInit(initPath: Path):
  """Read a package __init__.py into its public names and their sources.

  Two relative import shapes are understood: 'from . import submodule'
  binds a public name to a child, and 'from .module import Name' binds it
  to a documented symbol. Non-constant __all__ entries and absolute
  imports are passed over.

  Parameters
  ----------
  initPath : Path
      The __init__.py to read and parse.

  Returns
  -------
  tuple
      A pair '(allNames, sourceMap)'. 'allNames' is the list of public
      names in __all__. 'sourceMap' maps a public name to either
      '("child", childName)' or '("from", module, origName)'.
  """
  tree = ast.parse(initPath.read_text(encoding="utf-8"))
  allNames = []
  sourceMap = {}
  for node in tree.body:
    if isinstance(node, ast.Assign):
      isAll = any(
          isinstance(t, ast.Name) and t.id == "__all__"
          for t in node.targets
      )
      if isAll and isinstance(node.value, (ast.List, ast.Tuple)):
        allNames = [e.value for e in node.value.elts
                    if isinstance(e, ast.Constant)]
    elif isinstance(node, ast.ImportFrom) and node.level >= 1:
      if node.module is None:
        for alias in node.names:
          sourceMap[alias.asname or alias.name] = ("child", alias.name)
      else:
        for alias in node.names:
          key = alias.asname or alias.name
          sourceMap[key] = ("from", node.module, alias.name)
  return allNames, sourceMap
