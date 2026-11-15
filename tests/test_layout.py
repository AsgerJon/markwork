"""Tests for repository layout discovery: the source root and package from
the build configuration or convention, the tests in 'tests/' unless
another folder is named, with explicit overrides winning and an ambiguous
package failing loudly."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork._layout import (
    detectLayout, detectSrcRoot, detectPackageName, readPyproject,
)
from _support import EngineCase


class TestLayout(EngineCase):
  """Each detection step honours what the project declares, then falls back
  to convention; explicit overrides win and ambiguity raises."""

  #  Source root
  def test_src_root_from_setuptools_where(self):
    self.write(
        "pyproject.toml",
        "[tool.setuptools.packages.find]\nwhere = [\"lib\"]\n",
    )
    self.write("lib/pkg/__init__.py", "")
    data = readPyproject(self.root)
    self.assertEqual(detectSrcRoot(self.root, data), "lib")

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
  def test_tests_in_the_tests_folder_or_none(self):
    self.write("src/pkg/__init__.py", "")
    self.assertIsNone(detectLayout(self.root)[1])
    #  Nothing is searched for: tests kept anywhere else are not found.
    self.write("checks/test_a.py", "def test_a():\n  pass\n")
    self.assertIsNone(detectLayout(self.root)[1])
    (self.root / "tests").mkdir()
    self.assertEqual(detectLayout(self.root)[1], "tests")

  def test_tests_named_elsewhere(self):
    self.write("src/pkg/__init__.py", "")
    (self.root / "checks").mkdir()
    self.assertEqual(detectLayout(self.root, tests="checks")[1], "checks")
    #  A named folder that is not there is an error, not a silent miss.
    with self.assertRaises(RuntimeError) as caught:
      detectLayout(self.root, tests="nowhere")
    self.assertIn("nowhere", str(caught.exception))

  #  Whole layout
  def test_detect_layout_overrides_win(self):
    self.write("anywhere/mypkg/__init__.py", "")
    (self.root / "qa").mkdir()
    src, tests, pkg = detectLayout(
        self.root, src="anywhere", tests="qa", package="mypkg"
    )
    self.assertEqual((src, tests, pkg), ("anywhere", "qa", "mypkg"))

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


class TestLayoutEdges(EngineCase):
  """The degraded paths: no or broken pyproject.toml, setuptools settings
  of other shapes, and a flat layout with a tests package."""

  def test_read_pyproject_degrades(self):
    self.assertEqual(readPyproject(self.root), {})
    self.write("pyproject.toml", "this is = = not toml\n")
    self.assertEqual(readPyproject(self.root), {})
    self.write("pyproject.toml", "[project]\nname = 'x'\n")
    self.assertEqual(readPyproject(self.root), {"project": {"name": "x"}})

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
