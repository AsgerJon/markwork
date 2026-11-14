"""
The 'lexTokens' function lexes Python source into the merged token stream
the renderer consumes.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pygments.lexers import PythonLexer

from ._merge_tokens import mergeTokens

_LEXER = PythonLexer()


def lexTokens(source: str) -> list:
  """Lex source into '(offset, ttype, value)' tokens, merged the way the
  stock Pygments formatter groups them.

  The raw 'get_tokens_unprocessed' stream is used because it carries each
  token's absolute offset, and it applies none of the lexer's input
  preprocessing (no stripped leading newlines), so the offsets are offsets
  into 'source' itself. Lexing is the costly half of rendering, so a file
  shown on several pages is lexed once and its tokens reused.

  Parameters
  ----------
  source : str
      The source text.

  Returns
  -------
  list of tuple
      The merged tokens, in order.
  """
  return mergeTokens(_LEXER.get_tokens_unprocessed(source))
