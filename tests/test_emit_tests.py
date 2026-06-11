"""Tests for the test-tree mirror emission."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import markwork._gen as g
from _support import EngineCase


class TestEmitTests(EngineCase):
  """The test mirror renders each test file, recurses into a populated
  subdirectory, and skips __init__.py, __pycache__ and empty
  directories."""

  def setUp(self):
    super().setUp()
    self.configure()
    (self.root / "docs" / "_source").mkdir(parents=True)
    self.write("tests/test_a.py", "def test_a():\n  pass\n")
    self.write("tests/__init__.py", "")
    self.write("tests/sub/test_b.py", "def test_b():\n  pass\n")
    self.write("tests/__pycache__/junk.py", "junk = 1\n")
    (self.root / "tests" / "empty").mkdir()

  def test_tree(self):
    g._emit_test_dir(self.root / "tests")
    out = self.root / "docs" / "_source"
    names = {p.name for p in out.iterdir()}
    self.assertIn("tests.rst", names)
    self.assertIn("tests.test_a.rst", names)
    self.assertIn("tests.sub.rst", names)
    self.assertIn("tests.sub.test_b.rst", names)
    #  __init__, the bytecode cache and the empty directory are skipped.
    self.assertNotIn("tests.__init__.rst", names)
    self.assertNotIn("tests.empty.rst", names)
