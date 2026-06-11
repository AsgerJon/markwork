"""Tests for the highlighting renderer: equivalence with stock Pygments
and the invariant that stripping anchors restores that equivalence."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

import markwork._gen as g
from _support import EngineCase, strip_srcref


def _stock(source: str) -> str:
  """The reference HTML from the stock Pygments HtmlFormatter, configured
  to match the engine's inline line numbers and per-line spans."""
  formatter = HtmlFormatter(linenos="inline", linespans="line")
  return highlight(source, PythonLexer(), formatter)


ENGINE = Path(g.__file__).read_text(encoding="utf-8")

NO_NEWLINE = "import os\n\n\nx = os.getcwd()"


class TestHighlight(EngineCase):
  """Rendering with an empty link map is byte-identical to stock
  Pygments, and rendering with real links is byte-identical once the
  anchors are stripped."""

  def test_byte_identical_trailing_newline(self):
    self.assertEqual(g._highlight_with_links(ENGINE, {}), _stock(ENGINE))

  def test_byte_identical_no_trailing_newline(self):
    self.assertEqual(
        g._highlight_with_links(NO_NEWLINE, {}), _stock(NO_NEWLINE)
    )

  def test_strip_anchors_restores_equivalence(self):
    self.configure()
    pyfile = self.write(
        "src/demo/mod.py",
        "import os\n\n\ndef run():\n  return os.getcwd() + str(len([]))\n",
    )
    g._record_file_page(pyfile, "demo.mod")
    link_map = g._definition_links(pyfile)
    self.assertTrue(link_map)
    source = pyfile.read_text(encoding="utf-8")
    linked = g._highlight_with_links(source, link_map)
    self.assertIn('class="srcref', linked)
    self.assertEqual(strip_srcref(linked), _stock(source))
