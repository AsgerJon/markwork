"""
The 'buildBuiltinLinks' function maps every public builtin to its page on
docs.python.org.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import builtins

from ._pydocs import PYDOCS

_CONSTANTS = frozenset(
    {"True", "False", "None", "NotImplemented", "Ellipsis"}
)

#  The container types are listed on the built-in functions page under a
#  'func-<name>' anchor rather than a bare '<name>' (that bare anchor lives
#  on the standard types page instead). Every other builtin function or
#  type uses its plain '<name>' anchor there.
_FUNC_ANCHOR = frozenset(
    {
      "bytearray", "bytes", "dict", "frozenset", "list", "memoryview",
      "range", "set", "str", "tuple"
    }
)

#  Builtins added by the site module: documented in their own section of
#  the constants page rather than on the functions page.
_SITE_CONSTANTS = frozenset(
    {"copyright", "credits", "exit", "license", "quit"}
)


def buildBuiltinLinks() -> dict:
  """Map every public builtin name to its page on docs.python.org.

  Exceptions go to the exceptions page; the True/None family and the
  site-module builtins (quit, exit, ...) go to the constants page; the
  container types go to their 'func-<name>' anchor on the built-in
  functions page; and every other function or type goes to its plain
  anchor there.

  Returns
  -------
  dict
      A mapping of builtin name to its documentation URL.
  """
  links = {}
  for name in dir(builtins):
    if name.startswith("_"):
      continue
    if name in _CONSTANTS or name in _SITE_CONSTANTS:
      links[name] = "%slibrary/constants.html#%s" % (PYDOCS, name)
      continue
    member = getattr(builtins, name)
    if isinstance(member, type) and issubclass(member, BaseException):
      links[name] = "%slibrary/exceptions.html#%s" % (PYDOCS, name)
    elif name in _FUNC_ANCHOR:
      links[name] = "%slibrary/functions.html#func-%s" % (PYDOCS, name)
    else:
      links[name] = "%slibrary/functions.html#%s" % (PYDOCS, name)
  return links


#  Computed once at import: the link table the resolver consults for every
#  unshadowed builtin use.
BUILTIN_LINKS = buildBuiltinLinks()
