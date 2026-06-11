"""
The 'boundAnywhere' function collects every name bound anywhere in a file.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast


def boundAnywhere(tree: ast.AST) -> set:
  """Return every name bound anywhere in the file, at any scope.

  This covers assignments and deletions, parameters, class and function
  names, and import targets. A builtin whose name appears here is shadowed
  by local code, so its uses are left unlinked.

  Parameters
  ----------
  tree : ast.AST
      The parsed module.

  Returns
  -------
  set of str
      Every bound name found anywhere in the tree.
  """
  names = set()
  for node in ast.walk(tree):
    if isinstance(node, ast.Name) and isinstance(
        node.ctx, (ast.Store, ast.Del)
    ):
      names.add(node.id)
    elif isinstance(node, ast.arg):
      names.add(node.arg)
    elif isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    ):
      names.add(node.name)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
      for alias in node.names:
        names.add(alias.asname or alias.name.split(".")[0])
  return names
