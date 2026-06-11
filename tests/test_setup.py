"""Tests for the Sphinx extension entry point."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

import markwork
from markwork.engine import generate
from _support import FakeApp, FakeConfig


class TestSetup(unittest.TestCase):
  """setup(app) declares the configuration values, wires the generator to
  builder-inited, ships the stylesheet, and reports the extension
  metadata."""

  def setUp(self):
    self.app = FakeApp("conf", "src", FakeConfig())
    self.meta = markwork.setup(self.app)

  def test_config_values(self):
    self.assertEqual(
        set(self.app.config_values),
        {"markwork_package", "markwork_src_root", "markwork_tests_root"},
    )

  def test_generator_connected(self):
    self.assertIn(("builder-inited", generate), self.app.connected)

  def test_stylesheet_shipped(self):
    self.assertIn("markwork.css", self.app.css_files)
    self.assertTrue(
        any(
            path.endswith("etc")
            for path in self.app.config.html_static_path
        )
    )

  def test_metadata(self):
    self.assertEqual(self.meta["version"], markwork.__version__)
    self.assertFalse(self.meta["parallel_read_safe"])
    self.assertTrue(self.meta["parallel_write_safe"])
