"""Tests for one token's HTML rendering and the escape table."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

import markwork._gen as g


class TestTokenHtml(unittest.TestCase):
  """A token renders as escaped text, optionally inside a class span,
  optionally inside an internal or external go-to-definition anchor."""

  def test_plain_no_css_no_href(self):
    self.assertEqual(g._token_html("", "abc", ""), "abc")

  def test_css_span(self):
    self.assertEqual(
        g._token_html("n", "abc", ""), '<span class="n">abc</span>'
    )

  def test_internal_href(self):
    out = g._token_html("n", "abc", "page.html#line-3")
    self.assertEqual(
        out,
        '<a class="srcref" href="page.html#line-3">'
        '<span class="n">abc</span></a>',
    )

  def test_external_href(self):
    out = g._token_html("", "abc", "https://docs.python.org/3/x.html")
    self.assertIn('class="srcref srcref-ext"', out)
    self.assertIn('target="_blank"', out)
    self.assertIn('rel="noopener"', out)

  def test_escape_table_matches_pygments(self):
    #  Five markup characters escape, the apostrophe as decimal '&#39;'.
    self.assertEqual(
        g._token_html("", "<&>\"'", ""), "&lt;&amp;&gt;&quot;&#39;"
    )
