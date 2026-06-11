"""Live-anchor verification against docs.python.org. Every builtin in the
engine's table, and a sample of standard-library member anchors, must
exist on the real documentation pages, so drift in the docs structure is
caught. This test reaches the network and is skipped unless
MARKWORK_NETWORK is set in the environment; it is excluded from the
coverage accounting for the same reason. Anchors on the fetched pages are
read with the stdlib HTMLParser, never a regular expression."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import os
import unittest
import urllib.request
from html.parser import HTMLParser

from markwork.engine import buildBuiltinLinks, PYDOCS


class _IdCollector(HTMLParser):
  """Collect the value of every id attribute on a page."""

  def __init__(self):
    super().__init__()
    self.ids = set()

  def handle_starttag(self, tag, attrs):
    for name, value in attrs:
      if name == "id" and value is not None:
        self.ids.add(value)


def _page_ids(url):
  """Fetch a page and return the set of element ids on it."""
  handle = None
  try:
    handle = urllib.request.urlopen(url, timeout=30)
    text = handle.read().decode("utf-8")
  finally:
    if handle is not None:
      handle.close()
  parser = _IdCollector()
  parser.feed(text)
  return parser.ids


def _split(target):
  """Split a docs link into its page url and anchor fragment."""
  page, _, anchor = target.partition("#")
  return page, anchor


@unittest.skipUnless(
    os.environ.get("MARKWORK_NETWORK"), "network test, set MARKWORK_NETWORK"
)
class TestNetworkAnchors(unittest.TestCase):
  """The builtin table and a sample of standard-library anchors resolve
  on the live documentation."""

  def test_builtin_table(self):
    by_page = {}
    for target in buildBuiltinLinks().values():
      page, anchor = _split(target)
      by_page.setdefault(page, set()).add(anchor)
    for page, anchors in by_page.items():
      ids = _page_ids(page)
      missing = sorted(a for a in anchors if a not in ids)
      self.assertEqual(missing, [], "%s missing %s" % (page, missing))

  def test_stdlib_member_anchor(self):
    page = "%slibrary/os.html" % PYDOCS
    self.assertIn("os.getcwd", _page_ids(page))
