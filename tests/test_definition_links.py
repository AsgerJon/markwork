"""Tests for the go-to-definition link resolver, the densest part of the
engine: project-symbol, standard-library, same-file and builtin links,
each with its shadowing and self-page exclusions."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from _support import EngineCase

FUNCS = "https://docs.python.org/3/library/functions.html#"
LIB = "https://docs.python.org/3/library/"


class TestDefinitionLinks(EngineCase):
  """Each resolution kind and each exclusion is checked through the set
  of hrefs the resolver produces for a file."""

  def hrefs(self, docs, pyfile):
    return set(docs.definitionLinks(pyfile).values())

  def test_project_stdlib_builtin_and_selflink(self):
    docs = self.docs()
    docs.__symbol_def__[("demo.mod", "Thing")] = ("demo.mod.Thing", 10)
    pyfile = self.write(
        "src/demo/user.py",
        "from demo.mod import Thing\n"
        "import os\n"
        "helper = 1\n"
        "def run():\n"
        "  return Thing() + os.getcwd() + helper + len([])\n",
    )
    docs.recordFilePage(pyfile, "demo.user")
    hrefs = self.hrefs(docs, pyfile)
    self.assertIn("demo.mod.Thing.html#line-10", hrefs)
    self.assertIn("%sos.html" % LIB, hrefs)
    self.assertIn("%slen" % FUNCS, hrefs)
    self.assertIn("demo.user.html#line-3", hrefs)

  def test_self_page_star_nonstdlib_and_asname(self):
    docs = self.docs()
    docs.__symbol_def__[("demo.mod", "Same")] = ("demo.same", 1)
    pyfile = self.write(
        "src/demo/same.py",
        "from demo.mod import Same\n"
        "from os import *\n"
        "from external import Other\n"
        "import pygments\n"
        "import os.path\n"
        "import json as j\n"
        "value = Same\n",
    )
    docs.recordFilePage(pyfile, "demo.same")
    hrefs = self.hrefs(docs, pyfile)
    #  A symbol documented on this very page is not linked back to itself.
    self.assertNotIn("demo.same.html#line-1", hrefs)
    #  A no-asname dotted import links by its top package.
    self.assertIn("%sos.html" % LIB, hrefs)
    #  An asname import keeps the full module name.
    self.assertIn("%sjson.html" % LIB, hrefs)
    #  Third-party imports get no link.
    self.assertNotIn("%spygments.html" % LIB, hrefs)

  def test_stdlib_from_import(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/fromimp.py",
        "from os import getcwd\nvalue = getcwd()\n",
    )
    self.assertIn("%sos.html#os.getcwd" % LIB, self.hrefs(docs, pyfile))

  def test_shadowed_import_unlinked(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/shadow.py",
        "import os\nos = 5\nvalue = os\n",
    )
    self.assertNotIn("%sos.html" % LIB, self.hrefs(docs, pyfile))

  def test_no_bindings_and_shadowed_builtin(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/plain.py",
        "list = 1\nx = list\nsize = len([])\n",
    )
    hrefs = self.hrefs(docs, pyfile)
    #  len is a live builtin; list is shadowed by the assignment.
    self.assertIn("%slen" % FUNCS, hrefs)
    self.assertNotIn("%sfunc-list" % FUNCS, hrefs)

  def test_syntax_error_returns_empty(self):
    docs = self.docs()
    pyfile = self.write("src/demo/broken.py", "def (:\n")
    self.assertEqual(docs.definitionLinks(pyfile), {})

  def test_module_scope_nested_and_defline(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/scope.py",
        "acc = acc + 1\n"
        "config = 5\n"
        "def f():\n"
        "  config = 2\n"
        "  return config\n"
        "def run():\n"
        "  return acc + config\n",
    )
    docs.recordFilePage(pyfile, "demo.scope")
    links = docs.definitionLinks(pyfile)
    source = pyfile.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)

    def at(lineno, text):
      return sum(map(len, lines[:lineno - 1])) + lines[lineno - 1].index(text)

    #  acc is linked from its later use, not from its own definition line.
    self.assertEqual(links[at(7, "acc")], "demo.scope.html#line-1")
    self.assertNotIn(at(1, "acc + 1"), links)
    #  config in f is f's own local, so it is not linked; config in run
    #  is the module-level one, so it links to line 2.
    self.assertNotIn(at(5, "config"), links)
    self.assertEqual(links[at(7, "config")], "demo.scope.html#line-2")


class TestScopedLinks(EngineCase):
  """Links follow Python's scoping exactly: a local import links, a
  method or parameter of the same name shadows only its own scope, a star
  import or an ambiguous binding leaves names unlinked, and the
  attribute after an imported project module links to its symbol."""

  def links(self, docs, pyfile):
    """Map the identifier at each linked offset to its targets."""
    source = pyfile.read_text(encoding="utf-8")
    found = {}
    for offset, href in docs.definitionLinks(pyfile).items():
      end = offset
      while end < len(source) and (source[end].isalnum() or source[end] == "_"):
        end += 1
      found.setdefault(source[offset:end], set()).add(href)
    return found

  def test_local_import_and_method_shadowing(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/m.py",
        "def setup():\n"
        "  import json\n"
        "  return json.dumps\n"
        "class A:\n"
        "  def setup(self, id):\n"
        "    return id\n"
        "def other():\n"
        "  return setup(), id(1)\n",
    )
    docs.recordFilePage(pyfile, "demo.m")
    found = self.links(docs, pyfile)
    self.assertEqual(found["json"], {"%sjson.html" % LIB})
    self.assertEqual(found["setup"], {"demo.m.html#line-1"})
    #  The parameter 'id' shadows the builtin only inside the method.
    self.assertEqual(found["id"], {"%sid" % FUNCS})

  def test_star_import_and_ambiguity(self):
    docs = self.docs()
    pyfile = self.write(
        "src/demo/s.py",
        "from os import *\n"
        "try:\n"
        "  import tomllib\n"
        "except ImportError:\n"
        "  import tomli as tomllib\n"
        "from os import path\n"
        "path = 1\n"
        "x = len(open), tomllib, path\n",
    )
    found = self.links(docs, pyfile)
    #  'open' may be os.open here, so no builtin is linked at all.
    self.assertNotIn("len", found)
    self.assertNotIn("open", found)
    self.assertNotIn("tomllib", found)
    self.assertNotIn("path", found)

  def test_project_attribute_chains(self):
    docs = self.docs()
    self.write("src/demo/__init__.py", "")
    self.write("src/demo/mod.py", "class Thing:\n  pass\n")
    docs.__symbol_def__[("demo.mod", "Thing")] = ("demo.Thing", 1)
    docs.recordFilePage(self.root / "src/demo/mod.py", "demo.mod")
    docs.recordFilePage(self.root / "src/demo/__init__.py", "demo")
    pyfile = self.write(
        "src/demo/user.py",
        "import demo.mod\n"
        "import os.path\n"
        "from demo import mod as m\n"
        "x = demo.mod.Thing, demo.mod.Missing, os.path.join, m.Thing\n"
        "y = make().attr, demo.mod, x.real\n",
    )
    docs.recordFilePage(pyfile, "demo.user")
    found = self.links(docs, pyfile)
    self.assertEqual(found["Thing"], {"demo.Thing.html#line-1"})
    #  'import demo.mod' binds 'demo', the package; 'mod' after it, or
    #  imported from it, is the submodule.
    self.assertEqual(found["demo"], {"demo.html"})
    self.assertEqual(found["mod"], {"demo.mod.html"})
    self.assertEqual(found["m"], {"demo.mod.html"})
    self.assertEqual(found["os"], {"%sos.html" % LIB})
    #  Unknown project attributes and standard-library attributes are not
    #  linked: their anchors cannot be checked.
    for name in ("Missing", "path", "join", "attr", "real"):
      self.assertNotIn(name, found)

  def test_self_page_targets_unlinked(self):
    docs = self.docs()
    self.write("src/demo/__init__.py", "")
    pyfile = self.write(
        "src/demo/mod.py",
        "import demo\nimport demo.mod\nfrom demo import mod\n"
        "class Thing:\n  pass\nx = demo.mod.Thing, demo.mod, Thing\n",
    )
    docs.recordFilePage(pyfile, "demo.mod")
    docs.recordFilePage(self.root / "src/demo/__init__.py", "demo.mod")
    docs.__symbol_def__[("demo.mod", "Thing")] = ("demo.mod", 4)
    found = self.links(docs, pyfile)
    self.assertEqual(set(found), {"Thing"})

  def test_page_override_keeps_same_file_links_local(self):
    docs = self.docs()
    pyfile = self.write("src/demo/c.py", "value = 1\ncopy = value\n")
    docs.recordFilePage(pyfile, "demo.first")
    links = docs.definitionLinks(pyfile, "demo.second")
    self.assertEqual(set(links.values()), {"demo.second.html#line-1"})
