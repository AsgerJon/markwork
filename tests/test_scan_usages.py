"""Tests for the cross-reference usage scan."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from _support import EngineCase


class TestScanUsages(EngineCase):
  """An import binds a documented symbol for a file; its use lines are
  collected, falling back to the import line when the name is never used.
  Undocumented imports, a symbol's own page, __init__ files and files
  that do not parse contribute nothing."""

  def setUp(self):
    super().setUp()
    self.docs_ = self.docs()
    self.docs_.__symbol_page__[("demo.mod", "Thing")] = "demo.Thing"
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
    self.docs_.__file_page__["tests/test_self.py"] = "demo.Thing"

  def test_usage(self):
    usage = self.docs_.scanUsages(self.root / "tests")
    files = usage["demo.Thing"]
    self.assertEqual(files["tests/test_use.py"], [3])
    self.assertEqual(files["tests/test_unused.py"], [1])
    self.assertNotIn("tests/test_none.py", files)
    self.assertNotIn("tests/test_self.py", files)
    self.assertNotIn("tests/test_broken.py", files)


class TestScopedUsages(EngineCase):
  """Usages follow scoping: a plain import used through an attribute chain
  counts, a shadowed name does not, an ambiguous binding is skipped, and
  a plain import never used gives no fallback row."""

  def test_chains_shadowing_and_ambiguity(self):
    docs = self.docs()
    self.write("src/demo/__init__.py", "")
    self.write("src/demo/mod.py", "class Thing:\n  pass\n")
    docs.__symbol_page__[("demo.mod", "Thing")] = "demo.Thing"
    self.write(
        "tests/test_chain.py",
        "import demo.mod as dm\n"
        "def test():\n"
        "  local = 1\n"
        "  return dm.Thing(), dm.Other, make().Thing, local.real\n",
    )
    self.write(
        "tests/test_shadow.py",
        "from demo.mod import Thing\n"
        "def test(Thing):\n"
        "  return Thing\n",
    )
    self.write(
        "tests/test_ambiguous.py",
        "from demo.mod import Thing\n"
        "Thing = 1\n"
        "import demo.mod\n",
    )
    self.write("tests/test_self.py", "import demo.mod\nx = demo.mod.Thing\n")
    docs.__file_page__["tests/test_self.py"] = "demo.Thing"
    files = docs.scanUsages(self.root / "tests")["demo.Thing"]
    self.assertEqual(files["tests/test_chain.py"], [4])
    #  Shadowed by the parameter: the import line is the only row.
    self.assertEqual(files["tests/test_shadow.py"], [1])
    self.assertNotIn("tests/test_ambiguous.py", files)
    self.assertNotIn("tests/test_self.py", files)
