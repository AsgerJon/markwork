"""markwork run on its own source: the strongest end-to-end check there is.
The whole package must document without a single warning, every name in
every __all__ must get its page (including 'generate', which the top
package re-exports from the engine subpackage), and every internal line
anchor across the output must land on a real line."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import shutil
import tempfile
import unittest
from pathlib import Path

import markwork
from markwork.engine import SourceDocs, parseInit


def hrefTargets(text):
  """Each (stub, line) named by a real 'href="<stub>.html#line-N"'
  attribute. markwork's own tests hold that text in string literals too,
  but there it is escaped source, never an attribute, so only real
  attributes are read."""
  results = []
  index = text.find('href="')
  while index != -1:
    start = index + len('href="')
    end = text.find('"', start)
    stub, sep, line = text[start:end].partition(".html#line-")
    if sep:
      results.append((stub, line))
    index = text.find('href="', end)
  return results


class TestDogfood(unittest.TestCase):
  """The markwork tree documents itself cleanly and completely."""

  @classmethod
  def setUpClass(cls):
    pkg = Path(markwork.__file__).parent
    cls.src = pkg.parent
    cls.repo = cls.src.parent
    cls.out = Path(tempfile.mkdtemp())
    docs = SourceDocs(cls.repo, cls.src, pkg, cls.repo / "tests", cls.out)
    cls.warnings = docs.run()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.out, ignore_errors=True)

  def test_no_warnings(self):
    self.assertEqual(self.warnings, [])

  def test_every_public_name_has_a_page(self):
    for init in sorted((self.src / "markwork").rglob("__init__.py")):
      dotted = ".".join(init.parent.relative_to(self.src).parts)
      for name in parseInit(init)[0]:
        page = self.out / ("%s.%s.rst" % (dotted, name))
        self.assertTrue(page.exists(), "%s.%s has no page" % (dotted, name))

  def test_internal_anchors_resolve(self):
    anchors = []
    for path in self.out.iterdir():
      anchors += hrefTargets(path.read_text(encoding="utf-8"))
    self.assertTrue(anchors)
    for stub, lineno in anchors:
      frag = self.out / ("%s.frag.html" % stub)
      self.assertTrue(frag.exists(), "missing fragment for %s" % stub)
      body = frag.read_text(encoding="utf-8")
      self.assertIn('id="line-%s"' % lineno, body, stub)
