"""
The 'readSource' function reads a Python source file the way the
interpreter decodes it.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import io
import tokenize
from pathlib import Path


def readSource(pyfile: Path) -> str:
  """Return a source file's text, decoded the way Python decodes it.

  The encoding comes from a byte-order mark or a PEP 263 coding
  declaration and defaults to UTF-8, so a latin-1 file renders instead of
  crashing the run. A byte-order mark is dropped, since the parser rejects
  it in text, and line endings are normalised to '\\n'. A malformed coding
  declaration falls back to UTF-8, and bytes that do not decode are
  replaced rather than raised, so one bad file costs its own links and
  never the whole build.

  Parameters
  ----------
  pyfile : Path
      The source file to read.

  Returns
  -------
  str
      The decoded source text.
  """
  raw = pyfile.read_bytes()
  try:
    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
  except SyntaxError:
    encoding = "utf-8"
  text = raw.decode(encoding, errors="replace")
  return text.replace("\r\n", "\n").replace("\r", "\n")
