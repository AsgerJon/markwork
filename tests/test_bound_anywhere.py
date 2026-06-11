"""Tests for the bind-anywhere name scan."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import boundAnywhere

SOURCE = (
    "import mod\n"
    "def fn(arg):\n"
    "  x = 1\n"
    "  del x\n"
    "  class C:\n"
    "    pass\n"
    "  return arg\n"
)


class TestBoundAnywhere(unittest.TestCase):
  """Every name bound anywhere is collected: a stored name, a deleted
  name, a parameter, a class or function name, and an import target. A
  loaded name on its own is not a binding."""

  def test_bindings(self):
    names = boundAnywhere(ast.parse(SOURCE))
    self.assertEqual(names, {"mod", "fn", "arg", "x", "C"})
