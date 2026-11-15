"""Tests for the markwork command line: an ephemeral build renders a repo
to HTML without scaffolding anything into it, the source root is
auto-chosen, and the entry point drives the same build from an argument
vector. The builds use the stock 'alabaster' theme so they need no extra
package, and each writes to a temporary directory that is cleaned up."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import contextlib
import importlib
import io
import runpy
import shutil
import sys
import tempfile
import warnings
from pathlib import Path
from unittest import mock

from markwork._cli import build, defaultTheme, main, projectMeta
from _support import EngineCase, strip_srcref


class TestCli(EngineCase):
  """The CLI generates click-through HTML for a repository, leaves the
  repository untouched, auto-detects the source layout, and exposes the
  same build through main()."""

  def src_layout(self) -> None:
    """A small src/ project with one package, a re-export and a test."""
    self.write(
        "src/demo/__init__.py",
        "from .thing import Thing\n__all__ = ['Thing']\n",
    )
    self.write("src/demo/thing.py", "import os\nclass Thing:\n  pass\n")
    self.write(
        "tests/test_thing.py",
        "from demo.thing import Thing\ndef test_it():\n  assert Thing\n",
    )

  def fresh_output(self) -> Path:
    """A temporary output directory removed when the test ends."""
    out = Path(tempfile.mkdtemp())
    self.addCleanup(shutil.rmtree, out, ignore_errors=True)
    return out

  def test_build_renders_html_and_leaves_repo_clean(self):
    self.src_layout()
    out = self.fresh_output()
    result = build(self.root, output=out, theme="alabaster", quiet=True)
    self.assertEqual(result, out)
    #  The package and the re-exported symbol both render to HTML.
    self.assertTrue((out / "index.html").exists())
    self.assertTrue((out / "_source" / "demo.html").exists())
    page = (out / "_source" / "demo.Thing.html").read_text(encoding="utf-8")
    self.assertIn('class="highlight"', page)
    #  A go-to-definition anchor was injected into the rendered source.
    self.assertIn("srcref", page)
    self.assertNotEqual(strip_srcref(page), page)
    #  Nothing was scaffolded into the repository.
    self.assertFalse((self.root / "conf.py").exists())
    self.assertFalse((self.root / "docs").exists())
    self.assertFalse((self.root / "index.rst").exists())

  def test_pages_stay_small(self):
    #  A page's sidebar holds its own branch, not the whole site, and no
    #  copy of the generated rST is published.
    self.src_layout()
    self.write("src/demo/one/__init__.py", "from .a import A\n__all__ = ['A']\n")
    self.write("src/demo/one/a.py", "class A:\n  pass\n")
    self.write("src/demo/two/__init__.py", "from .b import B\n__all__ = ['B']\n")
    self.write("src/demo/two/b.py", "class B:\n  pass\n")
    self.write("src/demo/__init__.py",
               "from . import one, two\n__all__ = ['one', 'two']\n")
    out = self.fresh_output()
    build(self.root, output=out, theme="furo", quiet=True)
    page = (out / "_source" / "demo.one.A.html").read_text(encoding="utf-8")
    self.assertIn('href="demo.one.html"', page)
    self.assertIn('href="demo.two.html"', page)
    self.assertNotIn("demo.two.B.html", page)
    #  Sphinx makes the folder either way; nothing is copied into it.
    self.assertEqual(list((out / "_sources").rglob("*")), [])

  def test_source_root_auto_detected_without_src_dir(self):
    #  Package at the repo root, no src/ directory: the repo root is used.
    self.write(
        "demo/__init__.py", "from .thing import Thing\n__all__ = ['Thing']\n"
    )
    self.write("demo/thing.py", "class Thing:\n  pass\n")
    out = self.fresh_output()
    build(self.root, output=out, theme="alabaster", quiet=True)
    self.assertTrue((out / "_source" / "demo.html").exists())

  def test_main_builds_to_requested_output(self):
    self.src_layout()
    out = self.fresh_output()
    code = main(
        [str(self.root), "-o", str(out), "--theme", "alabaster", "-q"]
    )
    self.assertEqual(code, 0)
    self.assertTrue((out / "index.html").exists())

  def test_serial_and_parallel_builds_match(self):
    self.src_layout()
    serial, parallel = self.fresh_output(), self.fresh_output()
    main([str(self.root), "-o", str(serial), "-j", "1",
          "--theme", "alabaster", "-q"])
    main([str(self.root), "-o", str(parallel), "-j", "2",
          "--theme", "alabaster", "-q"])
    page = Path("_source") / "demo.Thing.html"
    self.assertEqual(
        (serial / page).read_text(encoding="utf-8"),
        (parallel / page).read_text(encoding="utf-8"),
    )

  def test_build_rejects_missing_repo(self):
    with self.assertRaises(NotADirectoryError):
      build(self.root / "does-not-exist", theme="alabaster", quiet=True)

  def test_project_meta_reads_pyproject(self):
    self.write(
        "pyproject.toml",
        "[project]\nname = \"sample\"\nversion = \"9.9.9\"\n",
    )
    self.assertEqual(projectMeta(self.root), ("sample", "9.9.9"))

  def test_project_meta_falls_back_to_dir_name(self):
    name, version = projectMeta(self.root)
    self.assertEqual(name, self.root.name)
    self.assertEqual(version, "")


class TestCliEdges(EngineCase):
  """The error paths exit cleanly with a message, the progress line and
  the default output directory work, --open opens the result, the theme
  falls back when furo is missing, and 'python -m markwork' runs main."""

  def src_layout(self) -> None:
    self.write("src/demo/__init__.py", "__all__ = []\n")

  def test_missing_repo_exits_1(self):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
      code = main([str(self.root / "nowhere"), "-q"])
    self.assertEqual(code, 1)
    self.assertIn("nowhere", err.getvalue())

  def test_sphinx_error_exits_2(self):
    self.src_layout()
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
      code = main([str(self.root), "--theme", "no_such_theme", "-q"])
    self.assertEqual(code, 2)
    self.assertIn("Sphinx stopped", err.getvalue())

  def test_progress_line_and_default_output(self):
    self.src_layout()
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
      result = build(self.root, theme="alabaster")
    self.addCleanup(shutil.rmtree, result, ignore_errors=True)
    self.assertTrue((result / "index.html").exists())
    self.assertIn("documenting demo under src/, tests: (none)", out.getvalue())

  def test_open_flag(self):
    self.src_layout()
    target = Path(tempfile.mkdtemp())
    self.addCleanup(shutil.rmtree, target, ignore_errors=True)
    with mock.patch("webbrowser.open") as opened, \
        contextlib.redirect_stdout(io.StringIO()):
      code = main([str(self.root), "-o", str(target), "-q", "--open",
                   "--theme", "alabaster"])
    self.assertEqual(code, 0)
    opened.assert_called_once_with((target / "index.html").as_uri())

  def test_default_theme(self):
    with mock.patch("importlib.util.find_spec", return_value=None):
      self.assertEqual(defaultTheme(), "alabaster")
    with mock.patch("importlib.util.find_spec", return_value=object()):
      self.assertEqual(defaultTheme(), "furo")

  def test_project_meta_with_unnamed_project(self):
    self.write("pyproject.toml", "[tool.x]\nkey = 1\n")
    self.assertEqual(projectMeta(self.root), (self.root.name, ""))
    #  A name without a version, and a version without a name.
    self.write("pyproject.toml", "[project]\nname = \"sample\"\n")
    self.assertEqual(projectMeta(self.root), ("sample", ""))
    self.write("pyproject.toml", "[project]\nversion = \"1.2\"\n")
    self.assertEqual(projectMeta(self.root), (self.root.name, "1.2"))
    #  A pyproject.toml that is no TOML names nothing.
    self.write("pyproject.toml", "[project\nname = \"sample\"\n")
    self.assertEqual(projectMeta(self.root), (self.root.name, ""))

  def test_module_entry_point(self):
    argv = ["markwork", "--help"]
    with mock.patch.object(sys, "argv", argv), \
        contextlib.redirect_stdout(io.StringIO()), \
        warnings.catch_warnings():
      warnings.simplefilter("ignore", RuntimeWarning)
      with self.assertRaises(SystemExit) as caught:
        runpy.run_module("markwork", run_name="__main__")
    self.assertEqual(caught.exception.code, 0)
    #  Imported rather than run, the module only exposes main.
    module = importlib.import_module("markwork.__main__")
    self.assertIs(module.main, main)
