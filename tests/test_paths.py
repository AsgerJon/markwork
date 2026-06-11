"""Tests for the path and rST naming helpers."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import markwork._gen as g
from _support import EngineCase


class TestPaths(EngineCase):
  """The dotted-name and repo-relative helpers, for both files and
  directories so the suffix-stripping branch is exercised either way."""

  def test_title(self):
    self.assertEqual(g._title("abc"), "abc\n===")

  def test_relpath(self):
    self.configure()
    path = self.write("src/demo/thing.py", "x = 1\n")
    self.assertEqual(g._relpath(path), "src/demo/thing.py")

  def test_src_dotted_file(self):
    self.configure()
    path = self.write("src/demo/sub/thing.py", "x = 1\n")
    self.assertEqual(g._src_dotted(path), "demo.sub.thing")

  def test_src_dotted_dir(self):
    self.configure()
    self.write("src/demo/sub/__init__.py", "")
    path = self.root / "src" / "demo" / "sub"
    self.assertEqual(g._src_dotted(path), "demo.sub")

  def test_repo_dotted_file(self):
    self.configure()
    path = self.write("tests/test_demo/test_thing.py", "x = 1\n")
    self.assertEqual(g._repo_dotted(path), "tests.test_demo.test_thing")

  def test_repo_dotted_dir(self):
    self.configure()
    self.write("tests/test_demo/test_thing.py", "x = 1\n")
    path = self.root / "tests" / "test_demo"
    self.assertEqual(g._repo_dotted(path), "tests.test_demo")
