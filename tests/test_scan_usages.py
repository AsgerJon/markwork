"""Tests for the cross-reference usage scan."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import markwork._gen as g
from _support import EngineCase


class TestScanUsages(EngineCase):
  """An import binds a documented symbol for a file; its use lines are
  collected, falling back to the import line when the name is never used.
  Undocumented imports, a symbol's own page, __init__ files and files
  that do not parse contribute nothing."""

  def setUp(self):
    super().setUp()
    self.configure()
    g.SYMBOL_PAGE[("demo.mod", "Thing")] = "demo.Thing"
    self.write("tests/__init__.py", "")
    self.write(
        "tests/test_use.py",
        "from demo.mod import Thing\ndef test():\n  return Thing()\n",
    )
    self.write(
        "tests/test_unused.py",
        "from demo.mod import Thing\nx = 1\n",
    )
    self.write(
        "tests/test_none.py",
        "from demo.mod import Missing\ny = 2\n",
    )
    self.write("tests/test_broken.py", "def (:\n")
    self.write("tests/test_self.py", "from demo.mod import Thing\n")
    g.FILE_PAGE["tests/test_self.py"] = "demo.Thing"

  def test_usage(self):
    usage = g._scan_usages(self.root / "tests")
    files = usage["demo.Thing"]
    self.assertEqual(files["tests/test_use.py"], [3])
    self.assertEqual(files["tests/test_unused.py"], [1])
    self.assertNotIn("tests/test_none.py", files)
    self.assertNotIn("tests/test_self.py", files)
    self.assertNotIn("tests/test_broken.py", files)
