"""Tests for package and leaf page emission driven by __all__."""
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
    "    'Own', 'missing_name',\n"
    "]\n"
)


class TestEmitPackage(EngineCase):
  """A package emits a page per public name: a child subpackage recurses,
  a child module is shown whole, a re-exported symbol is documented from
  its defining file, an own definition is documented in place, and the
  missing or non-exported cases produce nothing."""

  def setUp(self):
    super().setUp()
    self.out.mkdir(parents=True)
    self.write("src/demo/__init__.py", INIT)
    self.write("src/demo/subpkg/__init__.py", "__all__ = []\n")
    self.write("src/demo/leafmod.py", "leaf = 1\n")
    self.write("src/demo/things.py", "class Thing:\n  pass\n")
    self.docs_ = self.docs()

  def out_files(self):
    return {p.name for p in self.out.iterdir()}

  def test_pages_and_registries(self):
    self.docs_.emitPackage(self.root / "src" / "demo")
    names = self.out_files()
    self.assertIn("demo.rst", names)
    self.assertIn("demo.subpkg.rst", names)
    self.assertIn("demo.leafmod.rst", names)
    self.assertIn("demo.Thing.rst", names)
    self.assertIn("demo.Own.rst", names)
    #  Missing module, missing child, and the non-exported name are absent.
    self.assertNotIn("demo.Gone.rst", names)
    self.assertNotIn("demo.nothere.rst", names)
    #  The re-export registers under both the package and the module key.
    self.assertIn(("demo", "Thing"), self.docs_.__symbol_page__)
    self.assertIn(("demo.things", "Thing"), self.docs_.__symbol_page__)
    self.assertIn(("demo", "Own"), self.docs_.__symbol_page__)
    self.assertNotIn(("demo", "Gone"), self.docs_.__symbol_page__)
