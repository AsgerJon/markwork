"""Tests for the standard-library membership check."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

import markwork._gen as g


class TestIsStdlib(unittest.TestCase):
  """A module belongs to the standard library when its top-level package
  is a stdlib name; the empty string and third-party names do not."""

  def test_empty_module(self):
    self.assertFalse(g._is_stdlib(""))

  def test_stdlib(self):
    self.assertTrue(g._is_stdlib("os"))

  def test_stdlib_submodule(self):
    self.assertTrue(g._is_stdlib("collections.abc"))

  def test_third_party(self):
    self.assertFalse(g._is_stdlib("pygments"))
