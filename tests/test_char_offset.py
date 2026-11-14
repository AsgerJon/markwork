"""Tests for mapping an AST byte column to a character offset."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import charOffset, lineStarts


class TestCharOffset(unittest.TestCase):
  """An ASCII line maps byte columns straight through; a line holding
  wider characters is mapped back to characters, including the last line
  of a file without a trailing newline."""

  def check(self, source):
    starts = lineStarts(source)
    for node in ast.walk(ast.parse(source)):
      if isinstance(node, ast.Name):
        offset = charOffset(source, starts, node.lineno, node.col_offset)
        self.assertEqual(source[offset:offset + len(node.id)], node.id)

  def test_ascii(self):
    self.check("alpha = beta + gamma\n")

  def test_non_ascii_prefix(self):
    self.check("x = ['æøå', len]\ny = 'ü' + 'ß' + name\n")

  def test_non_ascii_identifier(self):
    self.check("søster = 1\nbror = søster\n")

  def test_last_line_without_newline(self):
    self.check("a = 1\nb = ['é', a]")
