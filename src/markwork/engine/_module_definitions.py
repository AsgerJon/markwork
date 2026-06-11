"""
The 'moduleDefinitions' function maps module-scope names to their first
definition line.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast


def moduleDefinitions(tree: ast.AST) -> dict:
  """Return each module-scope name mapped to the line it is defined on.

  Classes, functions, simple assignments and annotated assignments with a
  value are recorded; the first definition of a name wins. This is the
  go-to-definition target for a later use of that name within the same
  file.

  Parameters
  ----------
  tree : ast.AST
      The parsed module.

  Returns
  -------
  dict
      A mapping of name to its first definition line.
  """
  defs = {}
  for node in tree.body:
    if isinstance(
        node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    ):
      defs.setdefault(node.name, node.lineno)
    elif isinstance(node, ast.Assign):
      for target in node.targets:
        if isinstance(target, ast.Name):
          defs.setdefault(target.id, node.lineno)
    elif isinstance(node, ast.AnnAssign):
      if isinstance(node.target, ast.Name) and node.value is not None:
        defs.setdefault(node.target.id, node.lineno)
  return defs
