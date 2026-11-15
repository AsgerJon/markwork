"""
The 'tokenHtml' function renders one Pygments token to HTML, optionally
wrapped in a go-to-definition anchor.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import html

import pygments
from pygments.formatters import HtmlFormatter
from pygments.token import Token


def _stockText(text: str) -> str:
  """Return 'text' as the installed Pygments HtmlFormatter writes it when
  it is the text of a token, without the line end the formatter adds."""
  formatter = HtmlFormatter(nowrap=True)
  return pygments.format([(Token, text)], formatter).removesuffix("\n")


#  The character-to-entity table for the text of a token. The three
#  characters that begin or end markup are always escaped, so the safety
#  of a page never rests on Pygments. The two quotes need no escaping in
#  text content, and Pygments changed its mind about them: up to 2.20 it
#  wrote them as '&quot;' and '&#39;', from 2.21 on it leaves them as they
#  are. They are written here the way the installed Pygments writes them,
#  so a token's escaped text is byte-identical to stock Pygments either
#  way.
_ESCAPE = {
  ord("&"): "&amp;",
  ord("<"): "&lt;",
  ord(">"): "&gt;",
  ord('"'): _stockText('"'),
  ord("'"): _stockText("'"),
}


def tokenHtml(css: str, value: str, href: str) -> str:
  """Return the HTML for one token.

  The escaped text is wrapped in its Pygments class span when 'css' is
  given, and wrapped again in a go-to-definition anchor when 'href' is
  given. An external (docs.python.org) target gets a second class and
  opens in a new tab, so a jump to the Python docs does not navigate away
  from the project docs.

  Parameters
  ----------
  css : str
      The Pygments CSS class, or the empty string for no span.
  value : str
      The token's literal text.
  href : str or None
      The link target, or None or the empty string for no anchor. A
      target starting with 'http' is treated as external.

  Returns
  -------
  str
      The rendered HTML fragment for the token.
  """
  inner = value.translate(_ESCAPE)
  if css:
    inner = '<span class="%s">%s</span>' % (css, inner)
  if not href:
    return inner
  if href.startswith("http"):
    return ('<a class="srcref srcref-ext" target="_blank" rel="noopener" '
            'href="%s">%s</a>' % (html.escape(href, quote=True), inner))
  return '<a class="srcref" href="%s">%s</a>' % (
    html.escape(href, quote=True), inner
  )
