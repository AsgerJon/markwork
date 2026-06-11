"""Tests for the standard-library membership check."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

from markwork.engine import isStdlib


class TestIsStdlib(unittest.TestCase):
  """A module belongs to the standard library when its top-level package
  is a stdlib name; the empty string and third-party names do not."""

  def test_empty_module(self):
    self.assertFalse(isStdlib(""))

  def test_stdlib(self):
    self.assertTrue(isStdlib("os"))

  def test_stdlib_submodule(self):
    self.assertTrue(isStdlib("collections.abc"))

  def test_third_party(self):
    self.assertFalse(isStdlib("pygments"))
