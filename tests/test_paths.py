"""Tests for the title helper and the SourceDocs path methods."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork.engine import title
from _support import EngineCase


class TestPaths(EngineCase):
  """The title helper underlines text; the dotted-name and repo-relative
  methods handle both files and directories so the suffix-stripping branch
  is exercised either way."""

  def test_title(self):
    self.assertEqual(title("abc"), "abc\n===")

  def test_rel_path(self):
    path = self.write("src/demo/thing.py", "x = 1\n")
    self.assertEqual(self.docs().relPath(path), "src/demo/thing.py")

  def test_src_dotted_file(self):
    path = self.write("src/demo/sub/thing.py", "x = 1\n")
    self.assertEqual(self.docs().srcDotted(path), "demo.sub.thing")

  def test_src_dotted_dir(self):
    self.write("src/demo/sub/__init__.py", "")
    path = self.root / "src" / "demo" / "sub"
    self.assertEqual(self.docs().srcDotted(path), "demo.sub")

  def test_repo_dotted_file(self):
    path = self.write("tests/test_demo/test_thing.py", "x = 1\n")
    self.assertEqual(
        self.docs().repoDotted(path), "tests.test_demo.test_thing"
    )

  def test_repo_dotted_dir(self):
    self.write("tests/test_demo/test_thing.py", "x = 1\n")
    path = self.root / "tests" / "test_demo"
    self.assertEqual(self.docs().repoDotted(path), "tests.test_demo")
