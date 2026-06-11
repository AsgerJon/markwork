"""Tests for absolute-module resolution of imports."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork.engine import absModule
from _support import EngineCase


class TestAbsModule(EngineCase):
  """Absolute imports return their module verbatim; relative imports are
  resolved against the file's package, and a relative import outside the
  source root resolves to the empty string."""

  def setUp(self):
    super().setUp()
    self.src = self.root / "src"
    self.srcFile = self.write("src/demo/sub/mod.py", "x = 1\n")
    self.testFile = self.write("tests/test_mod.py", "x = 1\n")

  def test_absolute_with_module(self):
    self.assertEqual(
        absModule(self.src, self.srcFile, 0, "os.path"), "os.path"
    )

  def test_absolute_without_module(self):
    self.assertEqual(absModule(self.src, self.srcFile, 0, None), "")

  def test_relative_same_package(self):
    self.assertEqual(absModule(self.src, self.srcFile, 1, None), "demo.sub")

  def test_relative_with_module(self):
    self.assertEqual(
        absModule(self.src, self.srcFile, 1, "thing"), "demo.sub.thing"
    )

  def test_relative_parent_package(self):
    self.assertEqual(absModule(self.src, self.srcFile, 2, None), "demo")

  def test_relative_outside_source(self):
    self.assertEqual(absModule(self.src, self.testFile, 1, None), "")
