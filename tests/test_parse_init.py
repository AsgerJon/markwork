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
    "__all__ = [\"sub\", \"Thing\", undefined_name]\n"
)


class TestParseInit(EngineCase):
  """The re-export resolver reads __all__ and the relative import shapes,
  filters non-constant entries, keeps the asname binding, and passes over
  an absolute import."""

  def test_mixed(self):
    path = self.write("src/demo/__init__.py", MIXED)
    allNames, sourceMap = parseInit(path)
    self.assertEqual(allNames, ["sub", "Thing"])
    self.assertEqual(sourceMap["sub"], ("child", "sub"))
    self.assertEqual(sourceMap["T"], ("from", "mod", "Thing"))
    self.assertNotIn("X", sourceMap)

  def test_tuple_all(self):
    path = self.write("src/demo/__init__.py", "__all__ = ('a', 'b')\n")
    allNames, sourceMap = parseInit(path)
    self.assertEqual(allNames, ["a", "b"])
    self.assertEqual(sourceMap, {})

  def test_non_sequence_all_ignored(self):
    path = self.write("src/demo/__init__.py", "__all__ = make_all()\n")
    allNames, sourceMap = parseInit(path)
    self.assertEqual(allNames, [])
