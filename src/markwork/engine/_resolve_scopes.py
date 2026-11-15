"""
The 'resolveScopes' function builds the scope tree of a module and
resolves every name it loads to the scope that binds it.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast

from ._scope import Scope

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _parameters(args: ast.arguments) -> list:
  """Every parameter of a signature, in order, as ast.arg nodes."""
  found = list(args.posonlyargs) + list(args.args)
  if args.vararg is not None:
    found.append(args.vararg)
  found += list(args.kwonlyargs)
  if args.kwarg is not None:
    found.append(args.kwarg)
  return found


def _defaults(args: ast.arguments, scope: Scope) -> list:
  """The default values of a signature, paired with the scope that
  evaluates them: the one the function is defined in."""
  values = list(args.defaults)
  values += [value for value in args.kw_defaults if value is not None]
  return [(value, scope) for value in values]


def resolveScopes(tree: ast.AST) -> tuple:
  """Build the scope tree of a module and resolve every loaded name.

  The tree is walked once, iteratively, so a deeply nested expression
  cannot exhaust the recursion limit. Every binding is recorded on the
  scope it lands in: assignments, parameters, def and class names,
  imports, loop, with, except and match targets, walrus targets (which
  bind outside their comprehension) and PEP 695 type parameters. Each
  part of a definition is evaluated where Python evaluates it: decorators
  and defaults outside the function, annotations in its type-parameter
  scope, the first iterable of a comprehension outside it. Resolution
  runs after the walk, so a load that precedes its binding in a function
  still resolves to that function.

  Parameters
  ----------
  tree : ast.AST
      The parsed module.

  Returns
  -------
  tuple
      A pair '(scopes, uses)'. 'scopes' lists every Scope, the module
      first. 'uses' pairs each loaded ast.Name with the Scope that binds
      it, or with None when no scope does and it falls through to the
      builtins.
  """
  module = Scope("module")
  scopes = [module]
  loads = []

  def open_(kind: str, parent: Scope) -> Scope:
    scope = Scope(kind, parent)
    scopes.append(scope)
    return scope

  def typeScope(node: ast.AST, scope: Scope) -> tuple:
    params = node.type_params
    if not params:
      return scope, []
    inner = open_("function", scope)
    work = []
    for param in params:
      inner.bind(param.name)
      work += [(child, inner) for child in ast.iter_child_nodes(param)]
    return inner, work

  stack = [(tree, module)]
  while stack:
    node, scope = stack.pop()
    work = []
    if isinstance(node, _FUNCTIONS):
      work += [(item, scope) for item in node.decorator_list]
      work += _defaults(node.args, scope)
      outer, params = typeScope(node, scope)
      work += params
      for arg in _parameters(node.args):
        if arg.annotation is not None:
          work.append((arg.annotation, outer))
      if node.returns is not None:
        work.append((node.returns, outer))
      scope.bind(node.name)
      inner = open_("function", outer)
      for arg in _parameters(node.args):
        inner.bind(arg.arg)
      work += [(item, inner) for item in node.body]
    elif isinstance(node, ast.Lambda):
      work += _defaults(node.args, scope)
      inner = open_("function", scope)
      for arg in _parameters(node.args):
        inner.bind(arg.arg)
      work.append((node.body, inner))
    elif isinstance(node, ast.ClassDef):
      work += [(item, scope) for item in node.decorator_list]
      outer, params = typeScope(node, scope)
      work += params
      work += [(item, outer) for item in node.bases]
      work += [(item.value, outer) for item in node.keywords]
      scope.bind(node.name)
      inner = open_("class", outer)
      work += [(item, inner) for item in node.body]
    elif isinstance(node, _COMPREHENSIONS):
      inner = open_("comprehension", scope)
      for index, generator in enumerate(node.generators):
        work.append((generator.iter, inner if index else scope))
        work.append((generator.target, inner))
        work += [(item, inner) for item in generator.ifs]
      for field in ("elt", "key", "value"):
        child = getattr(node, field, None)
        if child is not None:
          work.append((child, inner))
    elif isinstance(node, ast.NamedExpr):
      target = scope
      while target.kind == "comprehension":
        target = target.parent
      target.bind(node.target.id)
      work.append((node.value, scope))
    elif isinstance(node, ast.Name):
      if isinstance(node.ctx, ast.Load):
        loads.append((node, scope))
      else:
        scope.bind(node.id)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
      for alias in node.names:
        if alias.name == "*":
          scope.starred = True
          continue
        local = alias.asname or alias.name.split(".")[0]
        owner = scope.bind(local, imported=True)
        if owner is not None:
          owner.imports.setdefault(local, []).append((node, alias))
    elif isinstance(node, ast.Global):
      scope.globals.update(node.names)
    elif isinstance(node, ast.Nonlocal):
      scope.nonlocals.update(node.names)
    elif isinstance(node, ast.TypeAlias):
      scope.bind(node.name.id)
      inner, params = typeScope(node, scope)
      work += params
      work.append((node.value, inner))
    else:
      #  'except E as name' and the match captures 'case name', '*name'
      #  and '**name' bind a plain string field, not an ast.Name.
      for field in ("name", "rest"):
        value = getattr(node, field, None)
        if isinstance(value, str):
          scope.bind(value)
      work += [(child, scope) for child in ast.iter_child_nodes(node)]
    stack.extend(reversed(work))
  uses = [(node, scope.resolve(node.id)) for node, scope in loads]
  return scopes, uses
