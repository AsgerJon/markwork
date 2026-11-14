"""
The 'charOffset' function turns an AST position into a character offset
into the source.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen


def charOffset(source: str, starts: list, lineno: int, col: int) -> int:
  """Return the absolute character offset of an AST position.

  The AST reports a column in UTF-8 bytes, while the source text and the
  Pygments token stream count characters. The two agree on an ASCII line;
  on any other line the byte column is mapped back to characters, so a
  name that follows 'æøå' on its line is still the token its link wraps.

  Parameters
  ----------
  source : str
      The source text.
  starts : list of int
      The per-line start offsets, as from 'lineStarts'.
  lineno : int
      The AST line number, counting from 1.
  col : int
      The AST column, in UTF-8 bytes.

  Returns
  -------
  int
      The offset of that position in 'source', in characters.

  Examples
  --------
  >>> charOffset('x = 1\\n', [0, 6], 1, 4)
  4
  >>> charOffset('s = "æ"; y\\n', [0, 11], 1, 10)
  9
  """
  start = starts[lineno - 1]
  end = starts[lineno] if lineno < len(starts) else len(source)
  line = source[start:end]
  if line.isascii():
    return start + col
  prefix = line.encode("utf-8")[:col]
  return start + len(prefix.decode("utf-8", errors="ignore"))
