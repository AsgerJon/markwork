"""
The 'tokenHtml' function renders one Pygments token to HTML, optionally
wrapped in a go-to-definition anchor.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import html

#  The exact character-to-entity table the Pygments HtmlFormatter uses for
#  text content, so a token's escaped text is byte-identical to stock
#  Pygments. It escapes the five markup-significant characters, rendering
#  the apostrophe as the decimal '&#39;' rather than Python html.escape's
#  hexadecimal '&#x27;'.
_ESCAPE = {
  ord("&"): "&amp;",
  ord("<"): "&lt;",
  ord(">"): "&gt;",
  ord('"'): "&quot;",
  ord("'"): "&#39;",
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
  href : str
      The link target, or the empty string for no anchor. A target
      starting with 'http' is treated as external.

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
