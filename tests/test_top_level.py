"""Tests for the top-level definition scanners."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from markwork.engine import topLevelDefs, topLevelDefLines
from _support import EngineCase

SOURCE = (
    "value = 1\n"
    "\n"
    "\n"
    "class Cls:\n"
    "  pass\n"
    "\n"
    "\n"
    "def func():\n"
    "  return None\n"
    "\n"
    "\n"
    "async def afunc():\n"
    "  return None\n"
)


class TestTopLevel(EngineCase):
  """Top-level classes and functions are collected, with assignments and
  other statements ignored; the line scanner records where each starts."""

  def test_defs(self):
    path = self.write("src/demo/mod.py", SOURCE)
    self.assertEqual(topLevelDefs(path), {"Cls", "func", "afunc"})

  def test_def_lines(self):
    path = self.write("src/demo/mod.py", SOURCE)
    self.assertEqual(
        topLevelDefLines(path),
        {"Cls": 4, "func": 8, "afunc": 12},
    )
