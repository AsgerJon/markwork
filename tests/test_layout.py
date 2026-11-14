"""Tests for repository layout discovery: the source root and package from
the build configuration or convention, and the tests root from pytest's
testpaths or convention, with explicit overrides winning and an ambiguous
package failing loudly."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import importlib
import sys
import types
import unittest
from unittest import mock

from markwork import _layout
from markwork._layout import (
    detectLayout, detectSrcRoot, detectPackageName, detectTestsRoot,
    pytestTestpaths, readPyproject, findTestFiles,
)
from _support import EngineCase


class TestLayout(EngineCase):
  """Each detection step honours what the project declares, then falls back
  to convention; explicit overrides win and ambiguity raises."""

  #  Source root
  @unittest.skipIf(_layout.tomllib is None, "no TOML parser (3.10, no tomli)")
  def test_src_root_from_setuptools_where(self):
    self.write(
        "pyproject.toml",
        "[tool.setuptools.packages.find]\nwhere = [\"lib\"]\n",
    )
    self.write("lib/pkg/__init__.py", "")
    data = readPyproject(self.root)
    self.assertEqual(detectSrcRoot(self.root, data), "lib")

  @unittest.skipIf(_layout.tomllib is None, "no TOML parser (3.10, no tomli)")
  def test_src_root_from_package_dir(self):
    self.write(
        "pyproject.toml",
        "[tool.setuptools]\npackage-dir = {\"\" = \"source\"}\n",
    )
    self.assertEqual(detectSrcRoot(self.root, readPyproject(self.root)), "source")

  def test_src_root_convention_src(self):
    self.write("src/pkg/__init__.py", "")
    self.assertEqual(detectSrcRoot(self.root, {}), "src")

  def test_src_root_convention_flat(self):
    self.write("pkg/__init__.py", "")
    self.assertEqual(detectSrcRoot(self.root, {}), ".")

  #  Package name
  def test_package_single(self):
    self.write("src/only/__init__.py", "")
    self.assertEqual(detectPackageName(self.root / "src", None), "only")

  def test_package_hint_disambiguates(self):
    self.write("src/one/__init__.py", "")
    self.write("src/two/__init__.py", "")
    self.assertEqual(detectPackageName(self.root / "src", "two"), "two")

  def test_package_ambiguous_raises(self):
    self.write("src/one/__init__.py", "")
    self.write("src/two/__init__.py", "")
    with self.assertRaises(RuntimeError):
      detectPackageName(self.root / "src", None)

  #  Tests root
  @unittest.skipIf(_layout.tomllib is None, "no TOML parser (3.10, no tomli)")
  def test_tests_from_pyproject_testpaths(self):
    self.write(
        "pyproject.toml",
        "[tool.pytest.ini_options]\ntestpaths = [\"suite\"]\n",
    )
    (self.root / "suite").mkdir()
    self.assertEqual(detectTestsRoot(self.root, readPyproject(self.root)), "suite")

  def test_tests_from_setup_cfg(self):
    self.write("setup.cfg", "[tool:pytest]\ntestpaths = checks\n")
    (self.root / "checks").mkdir()
    self.assertEqual(pytestTestpaths(self.root, {}), ["checks"])
    self.assertEqual(detectTestsRoot(self.root, {}), "checks")

  def test_tests_convention_test_singular(self):
    (self.root / "test").mkdir()
    self.assertEqual(detectTestsRoot(self.root, {}), "test")

  def test_tests_none(self):
    self.assertIsNone(detectTestsRoot(self.root, {}))

  #  Whole layout
  def test_detect_layout_overrides_win(self):
    self.write("anywhere/mypkg/__init__.py", "")
    src, tests, pkg = detectLayout(
        self.root, src="anywhere", tests="qa", package="mypkg"
    )
    self.assertEqual((src, tests, pkg), ("anywhere", "qa", "mypkg"))

  @unittest.skipIf(_layout.tomllib is None, "no TOML parser (3.10, no tomli)")
  def test_detect_layout_all_detected(self):
    self.write(
        "pyproject.toml",
        "[project]\nname = \"demo-pkg\"\n\n"
        "[tool.setuptools.packages.find]\nwhere = [\"src\"]\n",
    )
    self.write("src/demo_pkg/__init__.py", "")
    self.write("src/other/__init__.py", "")
    (self.root / "tests").mkdir()
    src, tests, pkg = detectLayout(self.root)
    #  The distribution name (normalised) disambiguates the two packages.
    self.assertEqual((src, tests, pkg), ("src", "tests", "demo_pkg"))

  def test_detect_layout_bad_package_override_raises(self):
    self.write("src/pkg/__init__.py", "")
    with self.assertRaises(RuntimeError):
      detectLayout(self.root, package="nope")

  #  Inert TestCase inheritance scan (no imports)
  def test_testfiles_direct_subclass(self):
    self.write(
        "qa/check_a.py",
        "import unittest\nclass A(unittest.TestCase):\n  pass\n",
    )
    self.assertEqual(findTestFiles(self.root), ["qa/check_a.py"])

  def test_testfiles_indirect_base_across_files(self):
    self.write(
        "qa/base.py",
        "import unittest\nclass Base(unittest.TestCase):\n  pass\n",
    )
    #  Not named test_*, base is a project class in another file: a plain
    #  glob misses it, the inheritance scan finds it.
    self.write(
        "qa/checks.py", "from base import Base\nclass FooChecks(Base):\n  pass\n"
    )
    self.assertEqual(
        findTestFiles(self.root), ["qa/base.py", "qa/checks.py"]
    )

  def test_testfiles_from_import_alias(self):
    self.write(
        "qa/c.py",
        "from unittest import TestCase as TC\nclass C(TC):\n  pass\n",
    )
    self.assertEqual(findTestFiles(self.root), ["qa/c.py"])

  def test_testfiles_ignores_plain_classes(self):
    self.write("qa/plain.py", "class Plain:\n  pass\n")
    self.assertEqual(findTestFiles(self.root), [])

  def test_tests_root_scan_dedicated_dir(self):
    self.write(
        "testing/base.py",
        "import unittest\nclass Base(unittest.TestCase):\n  pass\n",
    )
    self.write(
        "testing/checks.py",
        "from base import Base\nclass FooChecks(Base):\n  pass\n",
    )
    self.assertEqual(detectTestsRoot(self.root, {}, "src/demo"), "testing")

  def test_tests_root_scan_rejects_source_overlap(self):
    #  A test case living inside the documented package is not mirrored as
    #  tests, since that would render the source tree.
    self.write(
        "src/demo/helpers.py",
        "import unittest\nclass Helper(unittest.TestCase):\n  pass\n",
    )
    self.assertIsNone(detectTestsRoot(self.root, {}, "src/demo"))

  def test_detect_layout_tests_from_scan(self):
    self.write("pyproject.toml", "[project]\nname = \"demo\"\n")
    self.write("src/demo/__init__.py", "")
    self.write(
        "testing/base.py",
        "import unittest\nclass B(unittest.TestCase):\n  pass\n",
    )
    src, tests, pkg = detectLayout(self.root)
    self.assertEqual((src, tests, pkg), ("src", "testing", "demo"))


class TestLayoutEdges(EngineCase):
  """The degraded paths: no or broken pyproject.toml, every pytest config
  file, flat layouts with a tests package, environments under any name,
  and the class-graph corner cases of the inert test scan."""

  def test_read_pyproject_degrades(self):
    self.assertEqual(readPyproject(self.root), {})
    self.write("pyproject.toml", "this is = = not toml\n")
    self.assertEqual(readPyproject(self.root), {})
    self.write("pyproject.toml", "[project]\nname = 'x'\n")
    with mock.patch("markwork._layout.tomllib", None):
      self.assertEqual(readPyproject(self.root), {})

  def test_toml_parser_fallbacks(self):
    #  Simulate Python 3.10, with tomli and then without it, and restore.
    from markwork import _layout
    original = _layout.tomllib
    stand_in = types.ModuleType("tomli")
    try:
      with mock.patch.dict(sys.modules, {"tomllib": None, "tomli": stand_in}):
        importlib.reload(_layout)
        self.assertIs(_layout.tomllib, stand_in)
      with mock.patch.dict(sys.modules, {"tomllib": None, "tomli": None}):
        importlib.reload(_layout)
        self.assertIsNone(_layout.tomllib)
    finally:
      importlib.reload(_layout)
    self.assertIs(_layout.tomllib, original)

  def test_src_root_ignores_other_shapes(self):
    data = {"tool": {"setuptools": {
        "packages": ["pkg"], "package-dir": {"pkg": "lib"},
    }}}
    self.assertEqual(detectSrcRoot(self.root, data), ".")
    data = {"tool": {"setuptools": {"packages": {"find": {"where": []}}}}}
    self.assertEqual(detectSrcRoot(self.root, data), ".")

  def test_package_name_edges(self):
    with self.assertRaises(RuntimeError):
      detectPackageName(self.root / "missing", None)
    self.write("src/real/__init__.py", "")
    self.assertEqual(detectPackageName(self.root / "src", "other"), "real")

  def test_flat_layout_with_tests_package(self):
    #  tests/ and docs/ hold an __init__.py too, but are not the package.
    self.write("demo/__init__.py", "")
    self.write("tests/__init__.py", "")
    self.write("docs/__init__.py", "")
    self.assertEqual(detectLayout(self.root), (".", "tests", "demo"))

  def test_testpaths_from_every_config(self):
    data = {"tool": {"pytest": {"ini_options": {"testpaths": "a b"}}}}
    self.assertEqual(pytestTestpaths(self.root, data), ["a", "b"])
    self.write("tox.ini", "[tox]\nenvlist = py\n")
    self.write("pytest.ini", "[pytest]\ntestpaths = suite\n")
    self.assertEqual(pytestTestpaths(self.root, {}), ["suite"])
    self.write("setup.cfg", "not an ini file\n")
    self.assertEqual(pytestTestpaths(self.root, {}), ["suite"])

  def test_testpaths_never_the_source(self):
    self.write("pytest.ini", "[pytest]\ntestpaths = . src ./checks\n")
    (self.root / "checks").mkdir()
    self.write("src/demo/__init__.py", "")
    self.assertEqual(detectTestsRoot(self.root, {}, "src/demo"), "checks")
    self.write("pytest.ini", "[pytest]\ntestpaths = gone\n")
    self.assertIsNone(detectTestsRoot(self.root, {}, "src/demo"))

  def test_scan_skips_environments(self):
    case = "import unittest\nclass T(unittest.TestCase):\n  pass\n"
    self.write("myenv/pyvenv.cfg", "home = /usr\n")
    self.write("myenv/lib/site/foo/test_foo.py", case)
    (self.root / "conda_env" / "conda-meta").mkdir(parents=True)
    self.write("conda_env/lib/test_bar.py", case)
    self.write("pkg.egg-info/test_baz.py", case)
    self.write("vendor/site-packages/test_qux.py", case)
    self.write("qa/test_real.py", case)
    self.assertEqual(findTestFiles(self.root), ["qa/test_real.py"])

  def test_scan_class_graph_corners(self):
    self.write(
        "qa/graph.py",
        "import unittest as ut\n"
        "import os\n"
        "from unittest import mock, TestCase\n"
        "from collections import OrderedDict\n"
        "class A(B):\n  pass\n"
        "class B(A):\n  pass\n"
        "class C(pkg.Base, make()):\n  pass\n"
        "class D(ut.TestCase):\n  pass\n"
        "class E(TestCase):\n  pass\n",
    )
    self.write("qa/broken.py", "class (:\n")
    self.write("qa/cycle.py", "class A(B):\n  pass\nclass B(A):\n  pass\n")
    self.assertEqual(findTestFiles(self.root), ["qa/graph.py"])

  def test_scan_root_level_tests_rejected(self):
    case = "import unittest\nclass T(unittest.TestCase):\n  pass\n"
    self.write("test_top.py", case)
    self.write("qa/test_qa.py", case)
    self.assertIsNone(detectTestsRoot(self.root, {}))
