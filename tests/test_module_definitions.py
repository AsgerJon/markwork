"""Tests for the module-scope definition map."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import moduleDefinitions


class TestModuleDefinitions(unittest.TestCase):
  """Module-scope classes, functions, plain assignments and annotated
  assignments with a value are mapped to their first line; tuple targets
  and bare annotations are not."""

  def test_all_kinds(self):
    source = (
        "class Cls:\n"
        "  pass\n"
        "def func():\n"
        "  return None\n"
        "async def afunc():\n"
        "  return None\n"
        "plain = 1\n"
        "noted: int = 2\n"
        "a, b = 3, 4\n"
        "bare: int\n"
    )
    defs = moduleDefinitions(ast.parse(source))
    self.assertEqual(defs["Cls"], 1)
    self.assertEqual(defs["func"], 3)
    self.assertEqual(defs["afunc"], 5)
    self.assertEqual(defs["plain"], 7)
    self.assertEqual(defs["noted"], 8)
    #  A tuple assignment target is skipped.
    self.assertNotIn("a", defs)
    self.assertNotIn("b", defs)
    #  An annotation without a value is not a definition.
    self.assertNotIn("bare", defs)

  def test_first_definition_wins(self):
    source = "x = 1\nx = 2\n"
    self.assertEqual(moduleDefinitions(ast.parse(source))["x"], 1)
