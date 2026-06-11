"""Tests for the nested-scope binding scan."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

import markwork._gen as g

SOURCE = (
    "import top\n"
    "def outer(param):\n"
    "  local = 1\n"
    "  import sys\n"
    "  def inner():\n"
    "    pass\n"
    "  class Inner:\n"
    "    pass\n"
    "  return local + param + top\n"
)


class TestNestedBound(unittest.TestCase):
  """Names bound inside a nested scope are collected: an assignment, a
  parameter, a nested function or class, and a nested import. Names bound
  at module scope are not."""

  def test_nested_names(self):
    names = g._nested_bound(ast.parse(SOURCE))
    self.assertEqual(
        names, {"param", "local", "sys", "inner", "Inner"}
    )

  def test_module_names_excluded(self):
    names = g._nested_bound(ast.parse(SOURCE))
    self.assertNotIn("top", names)
    self.assertNotIn("outer", names)
