"""Tests for absolute-module resolution of imports."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import markwork._gen as g
from _support import EngineCase


class TestAbsModule(EngineCase):
  """Absolute imports return their module verbatim; relative imports are
  resolved against the file's package, and a relative import outside the
  source root resolves to the empty string."""

  def setUp(self):
    super().setUp()
    self.configure()
    self.src_file = self.write("src/demo/sub/mod.py", "x = 1\n")
    self.test_file = self.write("tests/test_mod.py", "x = 1\n")

  def test_absolute_with_module(self):
    self.assertEqual(g._abs_module(self.src_file, 0, "os.path"), "os.path")

  def test_absolute_without_module(self):
    self.assertEqual(g._abs_module(self.src_file, 0, None), "")

  def test_relative_same_package(self):
    self.assertEqual(g._abs_module(self.src_file, 1, None), "demo.sub")

  def test_relative_with_module(self):
    self.assertEqual(
        g._abs_module(self.src_file, 1, "thing"), "demo.sub.thing"
    )

  def test_relative_parent_package(self):
    self.assertEqual(g._abs_module(self.src_file, 2, None), "demo")

  def test_relative_outside_source(self):
    self.assertEqual(g._abs_module(self.test_file, 1, None), "")
