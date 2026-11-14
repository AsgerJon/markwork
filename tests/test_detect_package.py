"""Tests for package detection under the source root."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork.engine import detectPackage
from _support import EngineCase


class TestDetectPackage(EngineCase):
  """A configured name is honoured when it names a real package;
  otherwise a single package under the source root is found, and zero or
  several are ambiguous and raise. A missing source root raises too."""

  def test_named(self):
    self.write("src/given/__init__.py", "")
    src = self.root / "src"
    self.assertEqual(detectPackage(src, "given"), src / "given")

  def test_named_but_not_a_package(self):
    #  A directory without __init__.py is not a package: fail before the
    #  run instead of dying on a missing file in the middle of it.
    (self.root / "src" / "given").mkdir(parents=True)
    with self.assertRaises(RuntimeError) as caught:
      detectPackage(self.root / "src", "given")
    self.assertIn("markwork_package", str(caught.exception))

  def test_missing_source_root(self):
    with self.assertRaises(RuntimeError) as caught:
      detectPackage(self.root / "src", None)
    self.assertIn("markwork_src_root", str(caught.exception))

  def test_single_autodetected(self):
    self.write("src/only/__init__.py", "")
    self.write("src/only/mod.py", "x = 1\n")
    src = self.root / "src"
    self.assertEqual(detectPackage(src, None), src / "only")

  def test_none_found(self):
    src = self.root / "src"
    src.mkdir()
    with self.assertRaises(RuntimeError):
      detectPackage(src, None)

  def test_several_found(self):
    self.write("src/one/__init__.py", "")
    self.write("src/two/__init__.py", "")
    src = self.root / "src"
    with self.assertRaises(RuntimeError):
      detectPackage(src, None)
