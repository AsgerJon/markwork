"""
The 'topLevelDefs' function names the top-level classes and functions of a
file.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
from pathlib import Path


def topLevelDefs(pyfile: Path) -> set:
  """Return the names of classes and functions defined at the top level.

  Parameters
  ----------
  pyfile : Path
      The file to read and parse.

  Returns
  -------
  set of str
      The names of every module-level class, function and async
      function.
  """
  tree = ast.parse(pyfile.read_text(encoding="utf-8"))
  names = set()
  for node in tree.body:
    if isinstance(
        node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    ):
      names.add(node.name)
  return names
