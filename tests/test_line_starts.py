"""Tests for the line-offset helper."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

from markwork.engine import lineStarts


class TestLineStarts(unittest.TestCase):
  """Line starts index the offset at which each line begins, with the
  newline branch taken or not depending on the source."""

  def test_single_line_no_newline(self):
    self.assertEqual(lineStarts("abc"), [0])

  def test_multiple_lines(self):
    self.assertEqual(lineStarts("ab\ncd\n"), [0, 3, 6])

  def test_empty(self):
    self.assertEqual(lineStarts(""), [0])
