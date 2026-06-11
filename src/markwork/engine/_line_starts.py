"""
The 'lineStarts' function indexes where each source line begins.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen


def lineStarts(source: str) -> list:
  """Return the character offset at which each line begins.

  An AST node's '(lineno, col_offset)' is turned into an absolute offset
  into the source as 'starts[lineno - 1] + col_offset', so the rendered
  anchors land exactly without searching the text.

  Parameters
  ----------
  source : str
      The source text.

  Returns
  -------
  list of int
      The offset of the first character of each line. The first entry is
      always 0.

  Examples
  --------
  >>> lineStarts('ab\\ncd\\n')
  [0, 3, 6]
  """
  starts = [0]
  for index, char in enumerate(source):
    if char == "\n":
      starts.append(index + 1)
  return starts
