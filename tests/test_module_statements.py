"""Tests for listing the statements that run at module scope."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import moduleStatements

SOURCE = (
    "import a\n"
    "if a:\n"
    "  b = 1\n"
    "else:\n"
    "  c = 2\n"
    "try:\n"
    "  d = 3\n"
    "except E:\n"
    "  e = 4\n"
    "finally:\n"
    "  f = 5\n"
    "for g in h:\n"
    "  i = 6\n"
    "while j:\n"
    "  k = 7\n"
    "with l as m:\n"
    "  n = 8\n"
    "match o:\n"
    "  case 1:\n"
    "    p = 9\n"
    "def q():\n"
    "  r = 10\n"
    "class S:\n"
    "  t = 11\n"
)


class TestModuleStatements(unittest.TestCase):
  """Every block of if, try, for, while, with and match is module scope;
  function and class bodies are not, and the order is the source order."""

  def test_blocks(self):
    found = moduleStatements(ast.parse(SOURCE))
    assigned = [
      node.targets[0].id for node in found if isinstance(node, ast.Assign)
    ]
    self.assertEqual(assigned, list("bcdefikn") + ["p"])
