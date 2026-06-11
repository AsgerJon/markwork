"""Tests for appending a cross-reference section to a symbol page."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from _support import EngineCase


class TestAppendSection(EngineCase):
  """A section is appended only to a page that exists; a using file with
  a known page gets line links, one without gets bare line numbers."""

  def test_links_and_plain(self):
    self.out.mkdir(parents=True)
    (self.out / "demo.Thing.rst").write_text(
        "Thing\n=====\n", encoding="utf-8"
    )
    docs = self.docs()
    docs.__file_page__["src/demo/a.py"] = "demo.a"
    usage = {
        "demo.Thing": {"src/demo/a.py": [3, 5], "src/demo/b.py": [2]},
        "demo.Missing": {"src/demo/a.py": [1]},
    }
    docs.appendSection(usage, "Used in")
    body = (self.out / "demo.Thing.rst").read_text(encoding="utf-8")
    self.assertIn("Used in", body)
    self.assertIn('<a href="demo.a.html#line-3">3</a>', body)
    self.assertIn("<li>src/demo/b.py: 2</li>", body)
    #  The page that does not exist was skipped, writing no file.
    self.assertFalse((self.out / "demo.Missing.rst").exists())
