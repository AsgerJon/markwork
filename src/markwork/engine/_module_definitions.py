"""
The 'moduleDefinitions' function maps module-scope names to their first
definition line.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast

from ._module_statements import moduleStatements

_DEFS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def moduleDefinitions(tree: ast.AST) -> dict:
  """Return each module-scope name mapped to the line it is defined on.

  Classes, functions, assignments (including every name in a tuple or
  starred target), annotated assignments with a value and type aliases
  are recorded, wherever they sit at module scope: a definition inside an
  'if', 'try' or 'with' block counts just as a top-level one does. The
  first definition of a name wins. This is the go-to-definition target
  for a later use of that name within the same file.

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
  for node in moduleStatements(tree):
    if isinstance(node, _DEFS):
      defs.setdefault(node.name, node.lineno)
    elif isinstance(node, ast.Assign):
      pending = list(node.targets)
      while pending:
        target = pending.pop()
        if isinstance(target, ast.Name):
          defs.setdefault(target.id, node.lineno)
        elif isinstance(target, (ast.Tuple, ast.List)):
          pending.extend(target.elts)
        elif isinstance(target, ast.Starred):
          pending.append(target.value)
    elif isinstance(node, ast.AnnAssign):
      if isinstance(node.target, ast.Name) and node.value is not None:
        defs.setdefault(node.target.id, node.lineno)
    elif isinstance(node, ast.TypeAlias):
      defs.setdefault(node.name.id, node.lineno)
  return defs
