"""
The 'mergeTokens' function coalesces consecutive tokens of identical type.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen


def mergeTokens(stream) -> list:
  """Merge consecutive tokens of identical type into one.

  This is what Pygments' high-level 'get_tokens' does, so the rendered
  spans group exactly as the stock HtmlFormatter groups them and the
  output stays byte-identical once the anchors are stripped. The first
  token's offset is kept, which is also where any go-to-definition link
  for the run is anchored, since a link target always sits at a run's
  start.

  Parameters
  ----------
  stream : iterable of tuple
      Tuples of '(offset, ttype, value)', as produced by
      'get_tokens_unprocessed'.

  Returns
  -------
  list of tuple
      The merged tuples, in order.
  """
  merged = []
  for offset, ttype, value in stream:
    if merged and merged[-1][1] == ttype:
      prevOff, prevType, prevVal = merged[-1]
      merged[-1] = (prevOff, prevType, prevVal + value)
    else:
      merged.append((offset, ttype, value))
  return merged
