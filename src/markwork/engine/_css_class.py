"""
The 'cssClass' function resolves a Pygments token type to its short CSS
class.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pygments.token import STANDARD_TYPES


def cssClass(ttype: object) -> str:
  """Return the short Pygments CSS class for a token type.

  When the exact type is not in the standard table, the lookup walks up to
  a parent type. The root token maps to the empty string, meaning the
  token gets no wrapping span.

  Parameters
  ----------
  ttype : object
      A Pygments token type.

  Returns
  -------
  str
      The CSS class, for example 'n', 'k' or 's2', or the empty string
      for the root token.
  """
  node = ttype
  while node not in STANDARD_TYPES:
    node = node.parent
  return STANDARD_TYPES[node]
