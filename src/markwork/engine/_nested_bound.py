"""
The 'nestedBound' function collects names bound inside a nested scope.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast

_SCOPE_NODES = (
  ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
  ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
)


def nestedBound(tree: ast.AST) -> set:
  """Return the names bound inside a nested scope rather than at module
  scope.

  A nested scope is a function, lambda, comprehension or class body. A
  module-level name that also turns up here is shadowed somewhere in the
  file, so its uses are left unlinked rather than risk pointing at the
  wrong line.

  Parameters
  ----------
  tree : ast.AST
      The parsed module.

  Returns
  -------
  set of str
      Every name bound in a nested scope.
  """
  names = set()

  def walk(node: ast.AST, nested: bool) -> None:
    for child in ast.iter_child_nodes(node):
      if nested:
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
          names.add(child.id)
        elif isinstance(child, ast.arg):
          names.add(child.arg)
        elif isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
          names.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
          for alias in child.names:
            names.add(alias.asname or alias.name.split(".")[0])
      walk(child, nested or isinstance(child, _SCOPE_NODES))

  walk(tree, False)
  return names
