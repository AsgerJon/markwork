"""Tests for parsing a package __init__.py into its public mapping."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import markwork._gen as g
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
    all_names, source_map = g._parse_init(path)
    self.assertEqual(all_names, ["sub", "Thing"])
    self.assertEqual(source_map["sub"], ("child", "sub"))
    self.assertEqual(source_map["T"], ("from", "mod", "Thing"))
    self.assertNotIn("X", source_map)

  def test_tuple_all(self):
    path = self.write("src/demo/__init__.py", "__all__ = ('a', 'b')\n")
    all_names, source_map = g._parse_init(path)
    self.assertEqual(all_names, ["a", "b"])
    self.assertEqual(source_map, {})

  def test_non_sequence_all_ignored(self):
    path = self.write("src/demo/__init__.py", "__all__ = make_all()\n")
    all_names, source_map = g._parse_init(path)
    self.assertEqual(all_names, [])
