"""
The 'parseSource' function parses source text into a syntax tree without
letting a bad file stop the run.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import warnings


def parseSource(source: str):
  """Parse source text into a module tree, or return None when it does not
  parse.

  Compile-time warnings (an invalid escape sequence, say) are silenced: the
  documented code is read, never run, so its warnings are noise in the
  docs build. A file that fails to parse, holds a null byte or nests too
  deeply for the parser is rendered without links rather than failing the
  build.

  Parameters
  ----------
  source : str
      The source text.

  Returns
  -------
  ast.Module or None
      The parsed module, or None when the source does not parse.
  """
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
      return ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
      return None
