"""Tests for the builtin-to-docs link table."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

from markwork.engine import buildBuiltinLinks


class TestBuiltinLinks(unittest.TestCase):
  """Each kind of builtin routes to its own page on docs.python.org, and
  dunder names are left out entirely."""

  def setUp(self):
    self.links = buildBuiltinLinks()

  def test_no_dunders(self):
    self.assertNotIn("__import__", self.links)

  def test_constant(self):
    self.assertEqual(
        self.links["True"],
        "https://docs.python.org/3/library/constants.html#True",
    )

  def test_site_constant(self):
    self.assertEqual(
        self.links["quit"],
        "https://docs.python.org/3/library/constants.html#quit",
    )

  def test_exception(self):
    self.assertEqual(
        self.links["ValueError"],
        "https://docs.python.org/3/library/exceptions.html#ValueError",
    )

  def test_container_func_anchor(self):
    self.assertEqual(
        self.links["dict"],
        "https://docs.python.org/3/library/functions.html#func-dict",
    )

  def test_plain_function(self):
    self.assertEqual(
        self.links["len"],
        "https://docs.python.org/3/library/functions.html#len",
    )
