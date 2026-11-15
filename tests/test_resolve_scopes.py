"""Tests for the scope tree and name resolution: every load is resolved by
Python's own scoping rules to the scope that binds it, or to None for a
builtin."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest

from markwork.engine import Scope, resolveScopes


def resolve(source):
  """Map '(line, name)' of every load to the kind of scope that binds it,
  or None when it falls through to the builtins."""
  scopes, uses = resolveScopes(ast.parse(source))
  found = {}
  for node, scope in uses:
    found[(node.lineno, node.id)] = None if scope is None else scope.kind
  return scopes, found


class TestScope(unittest.TestCase):
  """The Scope methods bind and resolve directly."""

  def test_bind_and_resolve(self):
    module = Scope("module")
    func = Scope("function", module)
    func.globals.add("g")
    func.nonlocals.add("n")
    self.assertIs(func.bind("g"), module)
    self.assertIsNone(func.bind("n"))
    self.assertIs(func.bind("os", imported=True), func)
    self.assertTrue(func.binds("os") and module.binds("g"))
    self.assertIs(func.root(), module)
    self.assertIs(func.resolve("os"), func)
    self.assertIs(func.resolve("g"), module)
    self.assertIsNone(func.resolve("len"))


class TestResolveScopes(unittest.TestCase):
  """Each scoping rule Python applies is applied to the loads."""

  def test_module_function_and_builtin(self):
    _, found = resolve(
        "top = 1\n"
        "def f(param, *args, key=top, **kw):\n"
        "  local = param\n"
        "  return local, top, len, args, kw, key\n"
    )
    self.assertEqual(found[(2, "top")], "module")
    self.assertEqual(found[(3, "param")], "function")
    self.assertEqual(found[(4, "local")], "function")
    self.assertEqual(found[(4, "top")], "module")
    self.assertIsNone(found[(4, "len")])

  def test_load_before_local_binding_is_local(self):
    _, found = resolve("x = 1\ndef f():\n  print(x)\n  x = 2\n")
    self.assertEqual(found[(3, "x")], "function")

  def test_class_body_seen_only_from_inside(self):
    _, found = resolve(
        "size = 1\n"
        "class Box:\n"
        "  size = 2\n"
        "  double = size * 2\n"
        "  def get(self):\n"
        "    return size\n"
        "  squares = [size for _ in range(3)]\n"
    )
    self.assertEqual(found[(4, "size")], "class")
    #  A method, and a comprehension's body, skip the class scope.
    self.assertEqual(found[(6, "size")], "module")
    self.assertEqual(found[(7, "size")], "module")

  def test_comprehension_scopes(self):
    _, found = resolve(
        "items = []\n"
        "pairs = {k: v for k in items for v in k if v}\n"
        "gen = (total := n for n in items)\n"
    )
    self.assertEqual(found[(2, "items")], "module")
    self.assertEqual(found[(2, "k")], "comprehension")
    self.assertEqual(found[(2, "v")], "comprehension")
    self.assertEqual(found[(3, "n")], "comprehension")

  def test_walrus_binds_outside_comprehension(self):
    scopes, _ = resolve("def f(xs):\n  [y := x for x in [x for x in xs]]\n")
    func = [s for s in scopes if s.kind == "function"][0]
    self.assertIn("y", func.assigned)

  def test_global_and_nonlocal(self):
    scopes, found = resolve(
        "def f():\n"
        "  global counter\n"
        "  counter = 1\n"
        "  return counter\n"
        "def outer():\n"
        "  value = 0\n"
        "  def inner():\n"
        "    nonlocal value\n"
        "    value = 1\n"
        "    import value\n"
        "    return value\n"
        "  return inner\n"
    )
    self.assertIn("counter", scopes[0].assigned)
    self.assertEqual(found[(4, "counter")], "module")
    self.assertEqual(found[(11, "value")], "function")
    inner = [s for s in scopes if s.kind == "function"][-1]
    self.assertNotIn("value", inner.assigned | inner.imported)

  def test_lambda_decorators_and_annotations(self):
    _, found = resolve(
        "deco = kind = 1\n"
        "@deco\n"
        "def f(a: kind) -> kind:\n"
        "  return a\n"
        "g = lambda a, b=kind: a + b\n"
        "@deco\n"
        "class K(kind, metaclass=kind):\n"
        "  pass\n"
    )
    self.assertEqual(found[(2, "deco")], "module")
    self.assertEqual(found[(3, "kind")], "module")
    self.assertEqual(found[(5, "kind")], "module")
    self.assertEqual(found[(5, "a")], "function")
    self.assertEqual(found[(7, "kind")], "module")

  def test_except_and_match_captures(self):
    _, found = resolve(
        "try:\n"
        "  pass\n"
        "except KeyError as id:\n"
        "  print(id)\n"
        "except:\n"
        "  pass\n"
        "match data:\n"
        "  case [first, *rest]:\n"
        "    print(first, rest)\n"
        "  case {'k': value, **extra}:\n"
        "    print(value, extra)\n"
        "  case _:\n"
        "    pass\n"
    )
    for name, line in (("id", 4), ("first", 9), ("rest", 9),
                       ("value", 11), ("extra", 11)):
      self.assertEqual(found[(line, name)], "module", name)
    self.assertIsNone(found[(7, "data")])

  def test_imports(self):
    scopes, found = resolve(
        "import os.path\n"
        "import json as j\n"
        "from x import *\n"
        "def f():\n"
        "  from y import z\n"
        "  return os, j, z\n"
    )
    module = scopes[0]
    self.assertEqual(module.imported, {"os", "j"})
    self.assertTrue(module.starred)
    self.assertEqual([a.name for _, a in module.imports["os"]], ["os.path"])
    self.assertEqual(found[(6, "z")], "function")
    self.assertEqual(found[(6, "os")], "module")

  def test_type_parameters(self):
    _, found = resolve(
        "T = 1\n"
        "def first[T](items: list[T]) -> T:\n"
        "  return items[0]\n"
        "class Box[V: int]:\n"
        "  item: V\n"
        "type Pair[K] = tuple[K, K]\n"
        "type Plain = T\n"
    )
    self.assertEqual(found[(2, "T")], "function")
    self.assertEqual(found[(5, "V")], "function")
    self.assertEqual(found[(4, "int")], None)
    self.assertEqual(found[(6, "K")], "function")
    self.assertEqual(found[(7, "T")], "module")
