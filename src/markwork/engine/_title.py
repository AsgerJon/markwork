"""
The 'title' function builds an rST section title.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen


def title(text: str) -> str:
  """Return an rST title: the text underlined by '=' of equal length.

  Parameters
  ----------
  text : str
      The title text.

  Returns
  -------
  str
      The text followed by a newline and a rule of '=' the same width.

  Examples
  --------
  >>> title('abc')
  'abc\\n==='
  """
  return "%s\n%s" % (text, "=" * len(text))
