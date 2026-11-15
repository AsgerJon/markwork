"""Tests for the module-scope definition map."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import moduleDefinitions


class TestModuleDefinitions(unittest.TestCase):
  """Module-scope classes, functions, assignments (every name in a tuple,
  list or starred target) and annotated assignments with a value are
  mapped to their first line, wherever they sit at module scope; bare
  annotations, attribute targets and function or class bodies are not."""

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
        "[p, *rest] = 5, 6\n"
        "obj.attr = 7\n"
    )
    defs = moduleDefinitions(ast.parse(source))
    self.assertEqual(defs["Cls"], 1)
    self.assertEqual(defs["func"], 3)
    self.assertEqual(defs["afunc"], 5)
    self.assertEqual(defs["plain"], 7)
    self.assertEqual(defs["noted"], 8)
    #  Every name in a tuple, list or starred target is a definition.
    self.assertEqual((defs["a"], defs["b"]), (9, 9))
    self.assertEqual((defs["p"], defs["rest"]), (11, 11))
    #  An annotation without a value, or an attribute target, is not.
    self.assertNotIn("bare", defs)
    self.assertNotIn("obj", defs)
    self.assertNotIn("attr", defs)

  def test_first_definition_wins(self):
    source = "x = 1\nx = 2\n"
    self.assertEqual(moduleDefinitions(ast.parse(source))["x"], 1)

  def test_nested_module_blocks_count(self):
    source = (
        "try:\n"
        "  import tomllib\n"
        "except ImportError:\n"
        "  tomllib = None\n"
        "if True:\n"
        "  def compat():\n"
        "    inner = 1\n"
        "class Box:\n"
        "  member = 2\n"
    )
    defs = moduleDefinitions(ast.parse(source))
    self.assertEqual(defs["tomllib"], 4)
    self.assertEqual(defs["compat"], 6)
    #  Function and class bodies are their own scopes.
    self.assertNotIn("inner", defs)
    self.assertNotIn("member", defs)

  def test_type_alias(self):
    defs = moduleDefinitions(ast.parse("type Pair = tuple[int, int]\n"))
    self.assertEqual(defs["Pair"], 1)
