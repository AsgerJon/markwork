"""Tests for the Pygments CSS-class resolver."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

from pygments.token import Token, Name

import markwork._gen as g


class TestCssClass(unittest.TestCase):
  """The root token maps to the empty class without walking, while a
  leaf token type walks up to its nearest standard ancestor."""

  def test_root_token_empty(self):
    self.assertEqual(g._css_class(Token), "")

  def test_name_token(self):
    self.assertEqual(g._css_class(Name), "n")

  def test_leaf_walks_up(self):
    #  A type absent from the standard table resolves to its nearest
    #  standard ancestor's class, exercising the walk-up loop body.
    self.assertEqual(g._css_class(Name.FreshlyInvented), "n")
