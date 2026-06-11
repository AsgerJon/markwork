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
    hrefs = self.hrefs(docs, pyfile)
    #  acc is linked from its later use, not from its own definition line.
    self.assertIn("demo.scope.html#line-1", hrefs)
    #  config is bound inside f, so it is shadowed and never linked.
    self.assertNotIn("demo.scope.html#line-2", hrefs)
