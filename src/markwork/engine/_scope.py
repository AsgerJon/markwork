"""
The 'Scope' class is one lexical scope of a module: the names bound in it,
how each is bound, and the scope that encloses it.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen


class Scope:
  """One lexical scope and the names it binds.

  A load of a name is resolved the way Python resolves it: the scope it
  occurs in, then each enclosing function scope (a class body is seen only
  from directly inside it), then the module, and failing all of them the
  builtins. A 'global' declaration sends both loads and bindings of a name
  to the module; a 'nonlocal' one sends them to an enclosing function.

  Parameters
  ----------
  kind : str
      'module', 'function', 'class' or 'comprehension'. A lambda and a
      PEP 695 type-parameter scope count as 'function'.
  parent : Scope or None
      The enclosing scope, or None for the module.
  """

  def __init__(self, kind: str, parent=None) -> None:
    self.kind = kind
    self.parent = parent
    #  Names bound here by an import statement.
    self.imported = set()
    #  Names bound here any other way: assignment, def, class, parameter,
    #  loop, with, except or match target, deletion.
    self.assigned = set()
    #  Local name -> [(import node, alias)] for each import binding it.
    self.imports = {}
    self.globals = set()
    self.nonlocals = set()
    #  True once a star import binds names this scope cannot list, so an
    #  unbound name here may not be the builtin it looks like.
    self.starred = False

  def binds(self, name: str) -> bool:
    """Return whether this scope binds a name in any way.

    Parameters
    ----------
    name : str
        The name to look up.

    Returns
    -------
    bool
        True if the name is imported or assigned here.
    """
    return name in self.imported or name in self.assigned

  def root(self) -> "Scope":
    """Return the module scope at the root of the chain.

    Returns
    -------
    Scope
        The outermost enclosing scope.
    """
    scope = self
    while scope.parent is not None:
      scope = scope.parent
    return scope

  def bind(self, name: str, imported: bool = False):
    """Record a binding of a name made in this scope.

    A 'global' name binds in the module. A 'nonlocal' name is already
    bound by the enclosing function it refers to, so nothing is recorded.

    Parameters
    ----------
    name : str
        The bound name.
    imported : bool
        True when the binding is an import.

    Returns
    -------
    Scope or None
        The scope the binding landed in, or None for a nonlocal name.
    """
    if name in self.nonlocals:
      return None
    owner = self.root() if name in self.globals else self
    if imported:
      owner.imported.add(name)
    else:
      owner.assigned.add(name)
    return owner

  def resolve(self, name: str):
    """Return the scope a load of a name in this scope reads from.

    Parameters
    ----------
    name : str
        The loaded name.

    Returns
    -------
    Scope or None
        The binding scope, or None when no scope binds the name, so the
        load falls through to the builtins.
    """
    scope, first = self, True
    while scope.kind != "module" and name not in scope.globals:
      visible = first or scope.kind != "class"
      if visible and name not in scope.nonlocals and scope.binds(name):
        return scope
      scope, first = scope.parent, False
    module = scope.root()
    return module if module.binds(name) else None
