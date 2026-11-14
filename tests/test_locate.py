"""Tests for following a public name to the file that defines it, and the
lookups built on it: module files and pages, symbol targets and pages,
and the module an imported name is bound to."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast

from markwork.engine import resolveScopes
from _support import EngineCase

FILES = {
    "src/demo/__init__.py": (
        "from .core import Thing\n"
        "from .alias import Renamed as Public\n"
        "from demo.absolute import Abs\n"
        "from .starry import *\n"
        "from .loop_a import Loop\n"
        "from .broken import Broken\n"
        "own = 1\n"
    ),
    "src/demo/core/__init__.py": "from .thing import Thing\n",
    "src/demo/core/thing.py": "\n\nclass Thing:\n  pass\n",
    "src/demo/alias.py": "Renamed = 1\n",
    "src/demo/absolute.py": "Abs = 2\n",
    "src/demo/starry.py": "from .deep import *\n",
    "src/demo/deep.py": "Starred = 3\n",
    "src/demo/loop_a.py": "from .loop_b import Loop\n",
    "src/demo/loop_b.py": "from .loop_a import Loop\n",
    "src/demo/broken.py": "def (:\n",
}


class TestLocate(EngineCase):
  """A name is followed through subpackages, aliases, absolute imports
  and star imports to its definition; cycles, unparseable files and
  names outside the project give None."""

  def setUp(self):
    super().setUp()
    for rel, text in FILES.items():
      self.write(rel, text)
    self.docs_ = self.docs()

  def where(self, module, name):
    found = self.docs_.locate(module, name)
    if found is None:
      return None
    pyfile, line, keys = found
    return self.docs_.relPath(pyfile), line, keys

  def test_module_file(self):
    docs = self.docs_
    self.assertIsNone(docs.moduleFile(""))
    self.assertIsNone(docs.moduleFile("demo.nothing"))
    self.assertEqual(docs.relPath(docs.moduleFile("demo.core")),
                     "src/demo/core/__init__.py")
    self.assertEqual(docs.relPath(docs.moduleFile("demo.alias")),
                     "src/demo/alias.py")
    self.assertIsNone(docs.modulePage("demo.nothing"))

  def test_through_subpackage(self):
    self.assertEqual(
        self.where("demo", "Thing"),
        ("src/demo/core/thing.py", 3,
         [("demo", "Thing"), ("demo.core", "Thing"),
          ("demo.core.thing", "Thing")]),
    )

  def test_alias_absolute_star_and_own(self):
    self.assertEqual(self.where("demo", "Public")[:2], ("src/demo/alias.py", 1))
    self.assertEqual(self.where("demo", "Abs")[:2], ("src/demo/absolute.py", 1))
    self.assertEqual(self.where("demo", "Starred")[:2], ("src/demo/deep.py", 1))
    self.assertEqual(self.where("demo", "own")[:2], ("src/demo/__init__.py", 7))

  def test_dead_ends(self):
    self.assertIsNone(self.where("demo", "Loop"))
    self.assertIsNone(self.where("demo", "Broken"))
    self.assertIsNone(self.where("os", "getcwd"))
    #  A second lookup is answered from the cache.
    self.assertIsNone(self.where("demo", "Loop"))

  def test_symbol_target_and_page_fallbacks(self):
    docs = self.docs_
    #  Without a page of its own, a symbol links to any page showing its
    #  defining file, and has no usage page.
    self.assertIsNone(docs.symbolTarget("demo", "Thing"))
    docs.recordFilePage(self.root / "src/demo/core/thing.py", "demo.core.thing")
    self.assertEqual(docs.symbolTarget("demo", "Thing"), ("demo.core.thing", 3))
    self.assertIsNone(docs.symbolPage("demo", "Thing"))
    self.assertIsNone(docs.symbolPage("demo", "Loop"))
    #  A page registered under any key on the path is found from the top.
    docs.__symbol_page__[("demo.core.thing", "Thing")] = "demo.Thing"
    docs.__symbol_def__[("demo.core.thing", "Thing")] = ("demo.Thing", 3)
    self.assertEqual(docs.symbolPage("demo", "Thing"), "demo.Thing")
    self.assertEqual(docs.symbolTarget("demo.core", "Thing"), ("demo.Thing", 3))

  def test_bound_module(self):
    docs = self.docs_
    pyfile = self.write(
        "src/demo/user.py",
        "import demo.core\n"
        "import demo.alias as al\n"
        "from demo import core as c\n"
        "from . import alias\n"
        "import os\n"
        "import json\n"
        "json = 1\n"
        "import x\n"
        "import y as x\n",
    )
    scopes, _ = resolveScopes(ast.parse(pyfile.read_text(encoding="utf-8")))
    module = scopes[0]
    bound = lambda name: docs.boundModule(pyfile, module, name)
    self.assertEqual(bound("demo"), "demo")
    self.assertEqual(bound("al"), "demo.alias")
    self.assertEqual(bound("c"), "demo.core")
    self.assertEqual(bound("alias"), "demo.alias")
    self.assertEqual(bound("os"), "os")
    #  Assigned as well as imported, or imported two ways: ambiguous.
    self.assertIsNone(bound("json"))
    self.assertIsNone(bound("x"))
    self.assertIsNone(docs.boundModule(pyfile, None, "demo"))
    #  A relative import from outside the source root binds nothing known.
    test = self.write("tests/test_x.py", "from . import helper\n")
    tree = ast.parse("from . import helper\n")
    tscopes, _ = resolveScopes(tree)
    self.assertIsNone(docs.boundModule(test, tscopes[0], "helper"))


class TestLazyExports(EngineCase):
  """A module that resolves names on access through a module-level
  __getattr__ (PEP 562) is followed into it: a name the hook imports
  directly, and a name it reads off a module it imports, both lead to the
  real definition. A module candidate that lacks the name, or an import
  that is not a module, leads nowhere."""

  def setUp(self):
    super().setUp()
    self.write("src/demo/__init__.py", "")
    self.write(
        "src/demo/old/__init__.py",
        "__all__ = ['Moved', 'Read', 'Plain', 'Absent']\n"
        "def __getattr__(name):\n"
        "  if name == 'Moved':\n"
        "    from ..meta import Moved\n"
        "    return Moved\n"
        "  from ..new import flow\n"
        "  from ..new.flow import helper\n"
        "  import demo.plain\n"
        "  import json\n"
        "  return getattr(flow, name)\n",
    )
    self.write("src/demo/meta.py", "class Moved:\n  pass\n")
    self.write("src/demo/new/__init__.py", "")
    self.write("src/demo/new/flow.py", "\nclass Read:\n  pass\ndef helper():\n  pass\n")
    self.write("src/demo/plain.py", "Plain = 1\n")

  def test_lazy_names_followed(self):
    docs = self.docs()
    where = lambda name: docs.locate("demo.old", name)
    self.assertEqual(docs.relPath(where("Moved")[0]), "src/demo/meta.py")
    self.assertEqual(where("Read")[:2][1], 2)
    self.assertEqual(docs.relPath(where("Read")[0]), "src/demo/new/flow.py")
    self.assertEqual(docs.relPath(where("Plain")[0]), "src/demo/plain.py")
    self.assertIsNone(where("Absent"))

  def test_lazy_package_documents_without_warnings(self):
    self.write("src/demo/__init__.py", "from . import old\n__all__ = ['old']\n")
    docs = self.docs()
    warnings = docs.run()
    self.assertEqual(warnings, [repr("Absent").join(
        ["markwork: demo.old.__all__ lists ",
         ", but no definition, module or package of that name was found "
         "under src/demo/old"])])
    for name in ("Moved", "Read", "Plain"):
      self.assertTrue((self.out / ("demo.old.%s.rst" % name)).exists(), name)
