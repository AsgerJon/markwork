"""Tests for the consecutive-same-type token merge."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

from pygments.token import Name, Operator

import markwork._gen as g


class TestMergeTokens(unittest.TestCase):
  """Consecutive tokens of identical type fold into one, keeping the
  first offset; a differing type starts a fresh run."""

  def test_merges_runs(self):
    stream = [
        (0, Name, "a"),
        (1, Name, "b"),
        (2, Operator, "+"),
        (3, Name, "c"),
    ]
    self.assertEqual(
        g._merge_tokens(stream),
        [(0, Name, "ab"), (2, Operator, "+"), (3, Name, "c")],
    )

  def test_empty_stream(self):
    self.assertEqual(g._merge_tokens([]), [])
