"""Tests for the whole generation run and the Sphinx entry point."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork.engine import generate
from _support import EngineCase, FakeApp, FakeConfig

FILES = {
    "src/demo/__init__.py": (
        "from . import core\n"
        "from . import notpkg\n"
        "from .util import helper\n"
        "util_thing = 1\n"
        "__all__ = ['core', 'notpkg', 'helper', 'util_thing']\n"
    ),
    "src/demo/util.py": "helper = 1\n",
    "src/demo/core/__init__.py": (
        "from .thing import Thing\n__all__ = ['Thing']\n"
    ),
    "src/demo/core/thing.py": "class Thing:\n  pass\n",
    "tests/test_thing.py": (
        "from demo.core import Thing\ndef test_it():\n  assert Thing\n"
    ),
}


class TestRun(EngineCase):
  """A full run emits the package tree, the tests mirror, the packages
  index and the cross-references; the entry point resolves paths from a
  Sphinx application, and an instance may be run more than once."""

  def build(self, with_tests=True):
    for rel, text in FILES.items():
      if with_tests or not rel.startswith("tests/"):
        self.write(rel, text)
    #  A child named in __all__ whose directory is not a package.
    (self.root / "src" / "demo" / "notpkg").mkdir(parents=True)

  def test_generate_with_app(self):
    self.build()
    (self.root / "docs").mkdir()
    app = FakeApp(
        self.root / "docs", self.root / "docs", FakeConfig(package="demo")
    )
    generate(app)
    packages = (self.out / "_packages.txt").read_text(encoding="utf-8")
    #  The package is one rooted entry; its tree is reached through it.
    self.assertIn("_source/demo", packages)
    self.assertIn("_source/tests", packages)
    self.assertTrue((self.out / "demo.rst").exists())
    self.assertTrue((self.out / "demo.core.rst").exists())
    thing = (self.out / "demo.core.Thing.rst").read_text(encoding="utf-8")
    self.assertIn("Usage in testing", thing)
    self.assertTrue((self.out / "demo.core.Thing.frag.html").exists())

  def test_rerun_clears_existing_output(self):
    self.build()
    docs = self.docs()
    #  First run creates the output; the second finds it and clears it,
    #  exercising both sides of the existing-output check.
    docs.run()
    docs.run()
    self.assertTrue((self.out / "_packages.txt").exists())

  def test_run_without_tests(self):
    self.build(with_tests=False)
    self.docs().run()
    packages = (self.out / "_packages.txt").read_text(encoding="utf-8")
    self.assertNotIn("_source/tests", packages)
