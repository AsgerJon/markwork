"""Shared helpers for the markwork test suite: build a throwaway repo on
disk and hand back a SourceDocs pointed at it. Engine state lives on the
SourceDocs instance, so each test gets its own and there is nothing global
to reset."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import shutil
import tempfile
import unittest
from pathlib import Path

from markwork.engine import SourceDocs


def strip_srcref(html_text: str) -> str:
  """Remove the go-to-definition anchors from rendered HTML, keeping the
  text they wrap. Done with plain string scans rather than a parser, since
  the anchors never nest and their inner text holds no further anchor."""
  out = []
  index = 0
  while True:
    start = html_text.find('<a class="srcref', index)
    if start == -1:
      out.append(html_text[index:])
      return "".join(out)
    out.append(html_text[index:start])
    gt = html_text.find(">", start)
    end = html_text.find("</a>", gt)
    out.append(html_text[gt + 1:end])
    index = end + 4


class EngineCase(unittest.TestCase):
  """Base case that gives each test a fresh temporary repository and a
  factory for a SourceDocs pointed at it, then removes the repository
  afterwards."""

  def setUp(self) -> None:
    self.root = Path(tempfile.mkdtemp())

  def tearDown(self) -> None:
    shutil.rmtree(self.root, ignore_errors=True)

  def write(self, rel: str, text: str) -> Path:
    """Create a file under the repo root from a repo-relative posix path
    and text, making parent directories as needed."""
    path = self.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path

  @property
  def out(self) -> Path:
    """The output directory a run writes its pages to."""
    return self.root / "docs" / "_source"

  def docs(self, package: str = "demo") -> SourceDocs:
    """A SourceDocs over the repo with the standard src/tests layout."""
    src = self.root / "src"
    return SourceDocs(
        self.root, src, src / package, self.root / "tests", self.out
    )


class FakeConfig:
  """A stand-in for a Sphinx config object, holding only the values the
  engine and the extension setup read or mutate."""

  def __init__(
      self, package=None, src_root="src", tests_root="tests"
  ) -> None:
    self.html_static_path = []
    self.markwork_package = package
    self.markwork_src_root = src_root
    self.markwork_tests_root = tests_root


class FakeApp:
  """A stand-in for the Sphinx application, recording the wiring that
  setup(app) performs and exposing the directories generate() reads."""

  def __init__(self, confdir, srcdir, config) -> None:
    self.confdir = confdir
    self.srcdir = srcdir
    self.config = config
    self.connected = []
    self.css_files = []
    self.config_values = {}

  def add_config_value(self, name, default, rebuild) -> None:
    self.config_values[name] = default

  def connect(self, event, handler) -> None:
    self.connected.append((event, handler))

  def add_css_file(self, name) -> None:
    self.css_files.append(name)
