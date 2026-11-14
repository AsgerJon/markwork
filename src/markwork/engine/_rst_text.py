"""
The 'rstText' function makes plain text safe to place in rST as is.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

#  The characters rST may read as inline markup.
_MARKUP = frozenset("\\*`_|[]<>")


def rstText(text: str) -> str:
  """Return text with its whitespace collapsed and every character rST
  could read as inline markup backslash-escaped.

  Without this a name such as 'trailing_' becomes a hyperlink reference
  and its page title renders empty, and a README heading holding '*' or a
  backtick turns into markup it never meant.

  Parameters
  ----------
  text : str
      The plain text.

  Returns
  -------
  str
      The escaped text, which rST displays as the original.

  Examples
  --------
  >>> rstText('trailing_ name')
  'trailing\\\\_ name'
  """
  out = []
  for char in " ".join(text.split()):
    if char in _MARKUP:
      out.append("\\")
    out.append(char)
  return "".join(out)
