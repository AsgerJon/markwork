"""Tests for parsing a package __init__.py into its public mapping."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork.engine import parseInit
from _support import EngineCase

MIXED = (
    "version = \"1\"\n"
    "from . import sub\n"
    "from .mod import Thing as T\n"
    "from external import X\n"
    "from .. import parent\n"
    "__all__ = [\"sub\", \"Thing\", undefined_name, 3]\n"
)


class TestParseInit(EngineCase):
  """The re-export reader takes __all__ from a literal, follows literal
  extensions of it, and reports a missing or computed __all__ as None; it
  maps the relative import shapes, keeps the asname binding, and passes
  over absolute imports and imports from a parent package."""

  def parse(self, text):
    return parseInit(self.write("src/demo/__init__.py", text))

  def test_mixed(self):
    allNames, sourceMap = self.parse(MIXED)
    self.assertEqual(allNames, ["sub", "Thing"])
    self.assertEqual(sourceMap["sub"], ("child", "sub"))
    self.assertEqual(sourceMap["T"], ("from", "mod", "Thing"))
    self.assertNotIn("X", sourceMap)
    #  'from .. import parent' names the parent's child, not this one's.
    self.assertNotIn("parent", sourceMap)

  def test_tuple_all(self):
    allNames, sourceMap = self.parse("__all__ = ('a', 'b')\n")
    self.assertEqual(allNames, ["a", "b"])
    self.assertEqual(sourceMap, {})

  def test_missing_or_computed_all_is_none(self):
    self.assertIsNone(self.parse("x = 1\n")[0])
    self.assertIsNone(self.parse("__all__ = make_all()\n")[0])
    self.assertIsNone(self.parse("__all__: list\n")[0])

  def test_annotated_all(self):
    allNames, _ = self.parse("__all__: list[str] = ['a']\n")
    self.assertEqual(allNames, ["a"])

  def test_literal_extensions(self):
    allNames, _ = self.parse(
        "__all__ = ['a']\n"
        "__all__ += ['b']\n"
        "__all__.extend(('c',))\n"
        "__all__.append('d')\n"
        "__all__.sort()\n"
        "__all__.extend()\n"
        "other.extend(['nope'])\n"
        "print('not about __all__')\n"
        "'a docstring-like expression'\n"
    )
    self.assertEqual(allNames, ["a", "b", "c", "d"])

  def test_computed_extensions_make_all_unknown(self):
    for tail in (
        "__all__ += sub.__all__\n",
        "__all__.extend(sub.__all__)\n",
        "__all__.append(NAME)\n",
    ):
      self.assertIsNone(self.parse("__all__ = ['a']\n" + tail)[0], tail)
    #  Extending an __all__ that is already unknown keeps it unknown.
    self.assertIsNone(self.parse("__all__ += ['a']\n")[0])
    self.assertIsNone(self.parse("__all__.append('a')\n")[0])

  def test_unparseable_init(self):
    self.assertEqual(self.parse("def (:\n"), (None, {}))
