"""Tests for keeping each page's navigation tree to its own branch."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

from markwork.engine import collapseNavigation
from _support import FakeApp, FakeConfig


class TestCollapseNavigation(unittest.TestCase):
  """The page's toctree function is wrapped to always collapse, unless the
  project turns that off or the page has no toctree."""

  def setUp(self):
    self.calls = []
    self.app = FakeApp("conf", "src", FakeConfig())

  def toctree(self, **options):
    self.calls.append(options)
    return "<ul></ul>"

  def test_forces_collapse(self):
    context = {"toctree": self.toctree}
    collapseNavigation(self.app, "page", "page.html", context, None)
    html = context["toctree"](collapse=False, maxdepth=-1, titles_only=True)
    self.assertEqual(html, "<ul></ul>")
    self.assertEqual(self.calls, [
        {"collapse": True, "maxdepth": -1, "titles_only": True}
    ])

  def test_opt_out_and_no_toctree(self):
    self.app.config.markwork_collapse_navigation = False
    toctree = self.toctree
    context = {"toctree": toctree}
    collapseNavigation(self.app, "page", "page.html", context, None)
    self.assertIs(context["toctree"], toctree)
    self.app.config.markwork_collapse_navigation = True
    context = {}
    collapseNavigation(self.app, "page", "page.html", context, None)
    self.assertEqual(context, {})
