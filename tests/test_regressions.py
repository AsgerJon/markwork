"""Regression tests for the defects found in the 2026-11-07 review. Each
reproduces a reported failure on a throwaway repository: a re-export
through a subpackage dropped, links shifted by non-ASCII text, exception
and match captures not counted as bindings, plain-import usages missed,
and a non-UTF-8 source file crashing the run."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from _support import EngineCase

FUNCS = "https://docs.python.org/3/library/functions.html#"


class TestRegressions(EngineCase):
  """Each test is one reported defect, asserted on the engine's output."""

  def test_reexport_through_subpackage(self):
    self.write(
        "src/demo/__init__.py",
        "from .core import Thing\nfrom .a.b import Deep\n"
        "__all__ = ['Thing', 'Deep']\n",
    )
    self.write("src/demo/core/__init__.py", "from .thing import Thing\n")
    self.write("src/demo/core/thing.py", "\n\nclass Thing:\n  pass\n")
    self.write("src/demo/a/__init__.py", "")
    self.write("src/demo/a/b.py", "class Deep:\n  pass\n")
    docs = self.docs()
    docs.run()
    self.assertTrue((self.out / "demo.Thing.rst").exists())
    self.assertTrue((self.out / "demo.Deep.rst").exists())
    #  The definition line is the real one in the defining file.
    self.assertEqual(docs.__symbol_def__[("demo", "Thing")][1], 3)

  def test_non_ascii_text_keeps_links_on_their_names(self):
    docs = self.docs()
    pyfile = self.write("src/demo/u.py", "x = ['æøå', len([])]\n")
    source = pyfile.read_text(encoding="utf-8")
    starts = {source[offset:offset + 3] for offset in docs.definitionLinks(pyfile)}
    self.assertEqual(starts, {"len"})

  def test_except_and_match_captures_shadow_builtins(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/m.py",
        "try:\n  pass\nexcept KeyError as id:\n  print(id)\n"
        "match 1:\n  case len:\n    print(len)\n",
    )
    hrefs = set(docs.definitionLinks(pyfile).values())
    self.assertNotIn("%sid" % FUNCS, hrefs)
    self.assertNotIn("%slen" % FUNCS, hrefs)
    self.assertIn("%sprint" % FUNCS, hrefs)

  def test_plain_import_usage_is_listed(self):
    self.write(
        "src/demo/__init__.py", "from .mod import Thing\n__all__ = ['Thing']\n"
    )
    self.write("src/demo/mod.py", "class Thing:\n  pass\n")
    self.write(
        "tests/test_a.py", "import demo.mod\ndef test():\n  demo.mod.Thing()\n"
    )
    self.docs().run()
    page = (self.out / "demo.Thing.rst").read_text(encoding="utf-8")
    self.assertIn("tests/test_a.py", page)

  def test_coding_cookie_file_does_not_crash(self):
    path = self.root / "src" / "demo" / "__init__.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        b"# -*- coding: latin-1 -*-\nname = '\xe6\xf8\xe5'\n__all__ = ['name']\n"
    )
    self.docs().run()
    frag = (self.out / "demo.frag.html").read_text(encoding="utf-8")
    self.assertIn("æøå", frag)
