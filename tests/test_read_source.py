"""Tests for reading and parsing source files the way Python does."""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import warnings

from markwork.engine import readSource, parseSource
from _support import EngineCase


class TestReadSource(EngineCase):
  """A source file is decoded by its byte-order mark or coding
  declaration, its line endings are normalised, and undecodable bytes or
  a bad declaration degrade instead of raising."""

  def raw(self, data: bytes):
    path = self.root / "mod.py"
    path.write_bytes(data)
    return readSource(path)

  def test_utf8_default(self):
    self.assertEqual(self.raw("s = 'æøå'\n".encode("utf-8")), "s = 'æøå'\n")

  def test_coding_declaration(self):
    text = self.raw(b"# -*- coding: latin-1 -*-\ns = '\xe6'\n")
    self.assertTrue(text.endswith("s = 'æ'\n"))

  def test_byte_order_mark_dropped(self):
    text = self.raw(b"\xef\xbb\xbfx = 1\n")
    self.assertEqual(text, "x = 1\n")
    self.assertIsNotNone(parseSource(text))

  def test_line_endings_normalised(self):
    self.assertEqual(self.raw(b"a = 1\r\nb = 2\rc = 3\n"), "a = 1\nb = 2\nc = 3\n")

  def test_bad_declaration_and_bytes_degrade(self):
    text = self.raw(b"# coding: no-such-codec\ns = '\xff'\n")
    self.assertIn("\ufffd", text)


class TestParseSource(EngineCase):
  """Parsing returns the tree, or None for source that does not parse, and
  never lets the documented code's compile warnings through."""

  def test_parses(self):
    self.assertIsInstance(parseSource("x = 1\n"), ast.Module)

  def test_bad_source_is_none(self):
    self.assertIsNone(parseSource("def (:\n"))
    self.assertIsNone(parseSource("x = 1\0\n"))
    self.assertIsNone(parseSource("(" * 2000 + ")" * 2000 + "\n"))

  def test_compile_warnings_silenced(self):
    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter("always")
      self.assertIsNotNone(parseSource("pattern = '\\d+'\n"))
    self.assertEqual(caught, [])
