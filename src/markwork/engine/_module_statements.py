"""
The 'moduleStatements' function lists every statement that runs at module
scope.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast

#  Statement fields that hold a nested block of the same scope, in the
#  order they appear in source.
_BLOCKS = ("body", "handlers", "orelse", "finalbody", "cases")

#  Statements that open a new scope: their bodies are not module scope.
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def moduleStatements(tree: ast.AST) -> list:
  """Return every statement that runs at module scope, in source order.

  That is the top-level statements and those nested in the blocks of an
  if, for, while, with, try or match statement, since those blocks bind
  names in the module just as a top-level statement does. The body of a
  function or class is its own scope and is not entered.

  Parameters
  ----------
  tree : ast.AST
      The parsed module.

  Returns
  -------
  list of ast.stmt
      The module-scope statements, outer before inner, in source order.
  """
  found = []
  stack = list(reversed(tree.body))
  while stack:
    node = stack.pop()
    found.append(node)
    if isinstance(node, _SCOPES):
      continue
    nested = []
    for field in _BLOCKS:
      for child in getattr(node, field, ()):
        if isinstance(child, (ast.ExceptHandler, ast.match_case)):
          nested.extend(child.body)
        else:
          nested.append(child)
    stack.extend(reversed(nested))
  return found
