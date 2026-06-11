"""Tests for the line-offset helper."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

import markwork._gen as g


class TestLineStarts(unittest.TestCase):
  """Line starts index the offset at which each line begins, with the
  newline branch taken or not depending on the source."""

  def test_single_line_no_newline(self):
    self.assertEqual(g._line_starts("abc"), [0])

  def test_multiple_lines(self):
    self.assertEqual(g._line_starts("ab\ncd\n"), [0, 3, 6])

  def test_empty(self):
    self.assertEqual(g._line_starts(""), [0])
