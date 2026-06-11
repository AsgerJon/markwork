"""Every internal go-to-definition anchor must resolve: an href to
'<stub>.html#line-N' has to land on a '<span id="line-N">' in that stub's
rendered fragment. The anchors are located by plain string scans, never a
regular expression."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from _support import EngineCase

FILES = {
    "src/demo/__init__.py": (
        "from . import core\n__all__ = ['core']\n"
    ),
    "src/demo/core/__init__.py": (
        "from .thing import Thing\n"
        "from .util import shared\n"
        "__all__ = ['Thing', 'shared']\n"
    ),
    "src/demo/core/thing.py": (
        "import os\n\n\nclass Thing:\n"
        "  def where(self):\n    return os.getcwd()\n"
    ),
    "src/demo/core/util.py": (
        "shared = 1\n\n\ndef use():\n  return shared + shared\n"
    ),
    "tests/test_thing.py": (
        "from demo.core import Thing\ndef test_it():\n  assert Thing\n"
    ),
}


def internal_targets(text):
  """Each (stub, lineno) named by an internal line anchor in the text.
  The needle '.html#line-' appears only in internal anchors, never in the
  docs.python.org links, whose anchors are never line numbers."""
  needle = ".html#line-"
  results = []
  index = 0
  while True:
    hit = text.find(needle, index)
    if hit == -1:
      return results
    quote = text.rfind('"', 0, hit)
    stub = text[quote + 1:hit]
    start = hit + len(needle)
    end = start
    while end < len(text) and text[end].isdigit():
      end += 1
    results.append((stub, text[start:end]))
    index = end


class TestAnchors(EngineCase):
  """After a full run, every internal line anchor across the generated
  pages and fragments resolves to a real line span."""

  def test_internal_anchors_resolve(self):
    for rel, text in FILES.items():
      self.write(rel, text)
    self.docs().run()
    anchors = []
    for path in self.out.iterdir():
      anchors += internal_targets(path.read_text(encoding="utf-8"))
    #  There is at least one anchor to check, so the assertion is real.
    self.assertTrue(anchors)
    for stub, lineno in anchors:
      frag = self.out / ("%s.frag.html" % stub)
      self.assertTrue(frag.exists(), "missing fragment for %s" % stub)
      body = frag.read_text(encoding="utf-8")
      self.assertIn('id="line-%s"' % lineno, body)
