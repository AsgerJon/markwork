"""
The 'attributeChain' function splits a dotted attribute access into its
root name and the attributes after it.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast


def attributeChain(node: ast.Attribute):
  """Return the root name of an attribute chain and the attribute names
  that follow it.

  'pkg.mod.Thing' gives the 'pkg' Name node and ['mod', 'Thing']. A chain
  rooted in anything but a plain name, such as a call or a subscript,
  gives None, since its root cannot be resolved statically.

  Parameters
  ----------
  node : ast.Attribute
      The outermost attribute access.

  Returns
  -------
  tuple or None
      A pair '(root, attrs)' of the root ast.Name and the list of
      attribute names in order, or None.
  """
  attrs = []
  while isinstance(node, ast.Attribute):
    attrs.append(node.attr)
    node = node.value
  if not isinstance(node, ast.Name):
    return None
  attrs.reverse()
  return node, attrs
