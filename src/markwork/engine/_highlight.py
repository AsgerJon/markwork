"""
The 'highlightWithLinks' function renders source to highlighted HTML with
go-to-definition anchors injected.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import bisect

from pygments.lexers import PythonLexer

from ._css_class import cssClass
from ._line_starts import lineStarts
from ._merge_tokens import mergeTokens
from ._token_html import tokenHtml

_LEXER = PythonLexer()


def highlightWithLinks(source: str, linkMap: dict) -> str:
  """Render source to the highlighted HTML the Pygments HtmlFormatter
  produces, wrapping linked tokens in go-to-definition anchors.

  The output is a '.highlight' block with inline line numbers, each line
  wrapped in '<span id="line-N">' as the '#line-N' jump target and the
  ':target' highlight element. Every token whose start offset is a key of
  'linkMap' is wrapped in an anchor. The token stream from
  'get_tokens_unprocessed' carries each token's absolute offset, so the
  anchors land exactly without searching the text. A token holding
  newlines (a string or a run of blank lines) spans several line boxes and
  is never a link target, so it is split across the lines it covers.

  Parameters
  ----------
  source : str
      The source text.
  linkMap : dict
      A mapping of absolute source offset to link target.

  Returns
  -------
  str
      The highlighted HTML fragment.
  """
  starts = lineStarts(source)
  count = len(starts) - 1 if source.endswith("\n") else len(starts)
  buffers = [""] * (count + 1)
  for offset, ttype, value in mergeTokens(
      _LEXER.get_tokens_unprocessed(source)
      ):
    css = cssClass(ttype)
    if "\n" in value:
      first = bisect.bisect_right(starts, offset)
      for step, segment in enumerate(value.split("\n")):
        line = first + step
        if segment and line <= count:
          buffers[line] += tokenHtml(css, segment, "")
      continue
    line = bisect.bisect_right(starts, offset)
    buffers[line] += tokenHtml(css, value, linkMap.get(offset))
  #  Line numbers are right-aligned to the width of the largest, matching
  #  the Pygments HtmlFormatter so the gutter stays straight.
  width = len(str(count))
  parts = ['<div class="highlight"><pre><span></span>']
  for line in range(1, count + 1):
    parts.append(
      '<span id="line-%d"><span class="linenos">%s</span>%s\n'
      '</span>' % (line, str(line).rjust(width), buffers[line])
      )
  parts.append("</pre></div>\n")
  return "".join(parts)
