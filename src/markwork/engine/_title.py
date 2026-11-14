"""
The 'title' function builds an rST section title.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from ._rst_text import rstText


def title(text: str, underline: str = "=") -> str:
  """Return an rST title: the text, escaped by 'rstText', over a rule of
  the underline character at least as wide.

  Parameters
  ----------
  text : str
      The title text.
  underline : str
      The underline character, '=' by default.

  Returns
  -------
  str
      The escaped text, a newline and the rule.

  Examples
  --------
  >>> title('abc')
  'abc\\n==='
  >>> title('x_', '-')
  'x\\\\_\\n---'
  """
  escaped = rstText(text)
  return "%s\n%s" % (escaped, underline * len(escaped))
