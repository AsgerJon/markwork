"""
The 'isStdlib' function tests whether a module belongs to the standard
library.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import sys

_STDLIB = sys.stdlib_module_names


def isStdlib(module: str) -> bool:
  """Return whether a module belongs to the standard library.

  Membership is judged by the top-level package, so a submodule such as
  'collections.abc' resolves too.

  Parameters
  ----------
  module : str
      A dotted module name, or the empty string.

  Returns
  -------
  bool
      True if the top-level package is a standard-library module.

  Examples
  --------
  >>> isStdlib('collections.abc')
  True
  >>> isStdlib('')
  False
  """
  return True if module and module.split(".")[0] in _STDLIB else False
