"""
The 'parseInit' function reads a package __init__.py into its public
names and its child re-exports.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
from pathlib import Path

from ._module_statements import moduleStatements
from ._parse_source import parseSource
from ._read_source import readSource


def _literalNames(value: ast.AST):
  """The string entries of a literal list or tuple, or None when the value
  is anything else and so cannot be read without running the code."""
  if not isinstance(value, (ast.List, ast.Tuple)):
    return None
  return [
    item.value for item in value.elts
    if isinstance(item, ast.Constant) and isinstance(item.value, str)
  ]


def _isAll(node: ast.AST) -> bool:
  """Whether a node is the bare name '__all__'."""
  return isinstance(node, ast.Name) and node.id == "__all__"


def parseInit(initPath: Path):
  """Read a package __init__.py into its public names and their sources.

  __all__ is read from a literal list or tuple, whether assigned plainly
  or with an annotation, then extended by any literal '+=', '.extend()'
  or '.append()' that follows it at module scope. Non-string entries are
  passed over. An __all__ that is missing, or built in a way only running
  the code could reveal, gives None, which tells the caller to fall back
  to the package's conventionally public names. Two relative import
  shapes are mapped: 'from . import submodule' binds a public name to a
  child, and 'from .module import Name' binds it to a symbol.

  Parameters
  ----------
  initPath : Path
      The __init__.py to read and parse.

  Returns
  -------
  tuple
      A pair '(allNames, sourceMap)'. 'allNames' is the list of public
      names in __all__, or None when there is no readable __all__.
      'sourceMap' maps a public name to either '("child", childName)' or
      '("from", module, origName)'. A file that does not parse gives
      '(None, {})'.
  """
  tree = parseSource(readSource(initPath))
  if tree is None:
    return None, {}
  allNames = None
  sourceMap = {}
  for node in moduleStatements(tree):
    if isinstance(node, ast.Assign) and any(map(_isAll, node.targets)):
      allNames = _literalNames(node.value)
    elif isinstance(node, ast.AnnAssign) and _isAll(node.target):
      if node.value is not None:
        allNames = _literalNames(node.value)
    elif isinstance(node, ast.AugAssign) and _isAll(node.target):
      extra = _literalNames(node.value)
      known = allNames is not None and extra is not None
      allNames = allNames + extra if known else None
    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
      call = node.value
      func = call.func
      if isinstance(func, ast.Attribute) and _isAll(func.value):
        if allNames is not None and func.attr == "extend" and call.args:
          extra = _literalNames(call.args[0])
          allNames = allNames + extra if extra is not None else None
        elif allNames is not None and func.attr == "append" and call.args:
          item = call.args[0]
          known = isinstance(item, ast.Constant) and isinstance(item.value, str)
          allNames = allNames + [item.value] if known else None
    elif isinstance(node, ast.ImportFrom) and node.level >= 1:
      if node.module is None:
        if node.level == 1:
          for alias in node.names:
            sourceMap[alias.asname or alias.name] = ("child", alias.name)
      else:
        for alias in node.names:
          key = alias.asname or alias.name
          sourceMap[key] = ("from", node.module, alias.name)
  return allNames, sourceMap
