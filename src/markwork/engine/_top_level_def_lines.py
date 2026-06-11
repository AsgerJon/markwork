"""
The 'topLevelDefLines' function maps each top-level definition to its line.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
from pathlib import Path


def topLevelDefLines(pyfile: Path) -> dict:
  """Return each top-level class or function name mapped to its line.

  The line a definition starts on is the go-to-definition target within
  the file that defines it.

  Parameters
  ----------
  pyfile : Path
      The file to read and parse.

  Returns
  -------
  dict
      A mapping of definition name to the line number it starts on.
  """
  tree = ast.parse(pyfile.read_text(encoding="utf-8"))
  lines = {}
  for node in tree.body:
    if isinstance(
        node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    ):
      lines[node.name] = node.lineno
  return lines
