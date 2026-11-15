"""Tests for one token's HTML rendering and the escape table."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import unittest

import pygments
from pygments.formatters import HtmlFormatter
from pygments.token import Token

from markwork.engine import tokenHtml


class TestTokenHtml(unittest.TestCase):
  """A token renders as escaped text, optionally inside a class span,
  optionally inside an internal or external go-to-definition anchor."""

  def test_plain_no_css_no_href(self):
    self.assertEqual(tokenHtml("", "abc", ""), "abc")

  def test_css_span(self):
    self.assertEqual(
        tokenHtml("n", "abc", ""), '<span class="n">abc</span>'
    )

  def test_internal_href(self):
    out = tokenHtml("n", "abc", "page.html#line-3")
    self.assertEqual(
        out,
        '<a class="srcref" href="page.html#line-3">'
        '<span class="n">abc</span></a>',
    )

  def test_external_href(self):
    out = tokenHtml("", "abc", "https://docs.python.org/3/x.html")
    self.assertIn('class="srcref srcref-ext"', out)
    self.assertIn('target="_blank"', out)
    self.assertIn('rel="noopener"', out)

  def test_markup_characters_always_escape(self):
    #  These three begin or end markup, so they escape whatever the
    #  installed Pygments does.
    self.assertEqual(tokenHtml("", "<&>", ""), "&lt;&amp;&gt;")
    self.assertEqual(
        tokenHtml("s2", "</span><b>", ""),
        '<span class="s2">&lt;/span&gt;&lt;b&gt;</span>',
    )

  def test_escapes_as_the_installed_pygments(self):
    #  Pygments wrote the quotes in a token's text as entities up to 2.20
    #  and leaves them alone from 2.21 on. A token follows the installed
    #  one, character for character.
    text = "<&>\"' \"\"\"doc\"\"\" it's"
    stock = pygments.format([(Token, text)], HtmlFormatter(nowrap=True))
    self.assertEqual(tokenHtml("", text, "") + "\n", stock)
