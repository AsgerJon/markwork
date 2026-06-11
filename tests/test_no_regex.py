"""The engine is built without the regular-expression module, by design
and as the tool's signature. This check parses the engine and asserts no
re import or re attribute access survives, using the syntax tree rather
than a textual search."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import unittest
from pathlib import Path

import markwork._gen as g


def _re_references(source: str) -> list:
  """Every reference to the re module in the source: an import of re, a
  from-re import, or an attribute access on a name 're'."""
  found = []
  for node in ast.walk(ast.parse(source)):
    if isinstance(node, ast.Import):
      for alias in node.names:
        if alias.name.split(".")[0] == "re":
          found.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
      if (node.module or "").split(".")[0] == "re":
        found.append(node.module)
    elif isinstance(node, ast.Attribute):
      if isinstance(node.value, ast.Name) and node.value.id == "re":
        found.append("re.%s" % node.attr)
  return found


class TestNoRegex(unittest.TestCase):
  """The engine source contains no reference to the re module."""

  def test_engine_is_regex_free(self):
    source = Path(g.__file__).read_text(encoding="utf-8")
    self.assertEqual(_re_references(source), [])

  def test_detector_finds_each_shape(self):
    #  The detector itself must catch all three reference shapes, so it is
    #  exercised on a sample that uses each.
    sample = "import re\nfrom re import compile\nx = re.match('a', 'b')\n"
    self.assertEqual(
        _re_references(sample), ["re", "re", "re.match"]
    )
