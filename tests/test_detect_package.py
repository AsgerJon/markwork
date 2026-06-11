"""Tests for package detection under the source root."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import markwork._gen as g
from _support import EngineCase


class TestDetectPackage(EngineCase):
  """A configured name is honoured directly; otherwise a single package
  under the source root is found, and zero or several are ambiguous and
  raise."""

  def test_named(self):
    src = self.root / "src"
    src.mkdir()
    self.assertEqual(g._detect_package(src, "given"), src / "given")

  def test_single_autodetected(self):
    self.write("src/only/__init__.py", "")
    self.write("src/only/mod.py", "x = 1\n")
    src = self.root / "src"
    self.assertEqual(g._detect_package(src, None), src / "only")

  def test_none_found(self):
    src = self.root / "src"
    src.mkdir()
    with self.assertRaises(RuntimeError):
      g._detect_package(src, None)

  def test_several_found(self):
    self.write("src/one/__init__.py", "")
    self.write("src/two/__init__.py", "")
    src = self.root / "src"
    with self.assertRaises(RuntimeError):
      g._detect_package(src, None)
