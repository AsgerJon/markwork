"""
The 'addAliasSite' function records the source offset of an import alias'
name token.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast


def addAliasSite(
    sites: list, alias: ast.alias, starts: list, local: str
) -> None:
  """Record the source offset of an import alias' name token.

  This makes the name as it appears in the 'import' line itself a link.
  The position attributes on ast.alias are guaranteed from Python 3.10,
  markwork's floor, so no presence guard is needed.

  Parameters
  ----------
  sites : list
      The list of '(offset, local)' pairs to append to.
  alias : ast.alias
      The import alias node.
  starts : list of int
      The per-line start offsets, as from 'lineStarts'.
  local : str
      The local name the alias binds.
  """
  sites.append((starts[alias.lineno - 1] + alias.col_offset, local))
