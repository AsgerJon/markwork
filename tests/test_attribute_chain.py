"""Tests for splitting a dotted attribute access."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import attributeChain


class TestAttributeChain(unittest.TestCase):
  """A chain rooted at a name splits into the name and its attributes; one
  rooted at a call or a subscript has no static root."""

  def test_name_rooted(self):
    node = ast.parse("pkg.mod.Thing\n").body[0].value
    root, attrs = attributeChain(node)
    self.assertEqual((root.id, attrs), ("pkg", ["mod", "Thing"]))

  def test_call_rooted(self):
    node = ast.parse("make().value\n").body[0].value
    self.assertIsNone(attributeChain(node))
