"""Tests for package and leaf page emission driven by __all__, or by the
conventionally public names when there is no __all__."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from _support import EngineCase

INIT = (
    "from . import subpkg\n"
    "from . import leafmod\n"
    "from . import nothere\n"
    "from .things import Thing\n"
    "from .missing import Gone\n"
    "own = 1\n"
    "class Own:\n"
    "  pass\n"
    "class NotExported:\n"
    "  pass\n"
    "__all__ = [\n"
    "    'subpkg', 'leafmod', 'nothere', 'Thing', 'Gone',\n"
    "    'Own', 'missing_name', 'Thing', 'undeclared_mod',\n"
    "]\n"
)


class TestEmitPackage(EngineCase):
  """A package emits a page per public name: a child subpackage recurses,
  a child module is shown whole, a re-exported symbol is documented from
  its defining file, an own definition is documented in place, and each
  name in __all__ that resolves to nothing is reported."""

  def setUp(self):
    super().setUp()
    self.out.mkdir(parents=True)
    self.write("src/demo/__init__.py", INIT)
    self.write("src/demo/subpkg/__init__.py", "__all__ = []\n")
    self.write("src/demo/leafmod.py", "leaf = 1\n")
    self.write("src/demo/undeclared_mod.py", "value = 1\n")
    self.write("src/demo/things.py", "class Thing:\n  pass\n")
    self.docs_ = self.docs()

  def out_files(self):
    return {p.name for p in self.out.iterdir()}

  def test_pages_and_registries(self):
    self.docs_.emitPackage(self.root / "src" / "demo")
    names = self.out_files()
    for stub in ("demo", "demo.subpkg", "demo.leafmod", "demo.Thing",
                 "demo.Own", "demo.undeclared_mod"):
      self.assertIn("%s.rst" % stub, names)
    #  Missing module, missing child, and the non-exported name are absent.
    self.assertNotIn("demo.Gone.rst", names)
    self.assertNotIn("demo.nothere.rst", names)
    self.assertNotIn("demo.NotExported.rst", names)
    #  The re-export registers under both the package and the module key.
    self.assertIn(("demo", "Thing"), self.docs_.__symbol_page__)
    self.assertIn(("demo.things", "Thing"), self.docs_.__symbol_page__)
    self.assertIn(("demo", "Own"), self.docs_.__symbol_page__)
    self.assertNotIn(("demo", "Gone"), self.docs_.__symbol_page__)
    #  A name listed twice is one toctree entry.
    body = (self.out / "demo.rst").read_text(encoding="utf-8")
    self.assertEqual(body.count("   demo.Thing.rst\n"), 1)

  def test_unresolved_names_are_reported(self):
    self.docs_.emitPackage(self.root / "src" / "demo")
    reported = " ".join(self.docs_.__warnings__)
    for name in ("nothere", "Gone", "missing_name"):
      self.assertIn(repr(name), reported)
    self.assertEqual(len(self.docs_.__warnings__), 3)


class TestImpliedPublicNames(EngineCase):
  """Without a readable __all__, the public names are what the __init__
  defines or imports, then its submodules and subpackages, all without a
  leading underscore; a module already shown by a symbol page is not
  shown a second time, and nothing is reported missing."""

  def test_no_all(self):
    self.out.mkdir(parents=True)
    self.write(
        "src/demo/__init__.py",
        "from .widget import Widget\n"
        "from typing import Any\n"
        "from .helpers import *\n"
        "VERSION = '1'\n"
        "_private = 2\n",
    )
    self.write("src/demo/widget.py", "class Widget:\n  pass\n")
    self.write("src/demo/helpers.py", "def helper():\n  pass\n")
    self.write("src/demo/_internal.py", "x = 1\n")
    self.write("src/demo/tools/__init__.py", "")
    self.write("src/demo/tools/cut.py", "def cut():\n  pass\n")
    (self.root / "src/demo/notpkg").mkdir()
    (self.root / "src/demo/data.txt").write_text("x", encoding="utf-8")
    docs = self.docs()
    docs.emitPackage(self.root / "src" / "demo")
    names = {p.stem for p in self.out.glob("*.rst")}
    self.assertEqual(
        names,
        {"demo", "demo.Widget", "demo.VERSION", "demo.helpers",
         "demo.tools", "demo.tools.cut"},
    )
    self.assertEqual(docs.__warnings__, [])

  def test_unparseable_init(self):
    self.out.mkdir(parents=True)
    self.write("src/demo/__init__.py", "def (:\n")
    self.write("src/demo/mod.py", "x = 1\n")
    docs = self.docs()
    docs.emitPackage(self.root / "src" / "demo")
    self.assertTrue((self.out / "demo.mod.rst").exists())
